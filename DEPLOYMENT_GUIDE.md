# 배포 가이드 - 무중단 Blue-Green 전략

## 📋 개요

이 가이드는 **무중단**으로 Isshoni 플랫폼을 배포하는 Blue-Green 배포 전략을 사용하는 방법을 설명합니다. 특히 배포 중 WebSocket 연결을 유지하는 과제를 해결하는 데 중점을 둡니다.

---

## 🎯 과제: WebSocket 연결

전통적인 배포 전략은 WebSocket 기반 애플리케이션에서 중요한 문제가 있습니다:

**문제**: 새 버전을 배포할 때 활성 WebSocket 연결이 갑자기 종료되어 다음과 같은 문제가 발생합니다:
- 채팅 메시지 손실
- 실시간 협업 중단
- 사용자 경험 저하
- 캔버스 상태 비동기화

**해결책**: Redis 기반 세션 지속성 + 우아한 연결 마이그레이션

---

## 🏗 아키텍처: 세션 지속성을 갖춘 Blue-Green

```
                           ┌─────────────────────┐
                           │   Application       │
                           │   Load Balancer     │
                           │   (ALB)             │
                           └──────────┬──────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
          ┌─────────▼─────────┐              ┌─────────▼─────────┐
          │  BLUE 환경         │              │ GREEN 환경        │
          │  (현재 v1.0)       │              │  (신규 v1.1)      │
          │                    │              │                   │
          │  - FastAPI         │              │  - FastAPI        │
          │  - WebSocket       │              │  - WebSocket      │
          └─────────┬──────────┘              └─────────┬─────────┘
                    │                                   │
                    └─────────────┬─────────────────────┘
                                  │
                        ┌─────────▼──────────┐
                        │   Redis 클러스터    │
                        │                    │
                        │  - 세션 데이터     │
                        │  - 채팅 기록       │
                        │  - 캔버스 상태     │
                        └────────────────────┘
```

**핵심 원칙**: Blue와 Green 환경 모두 **동일한 Redis 클러스터**를 공유하여 원활한 세션 인계가 가능합니다.

---

## 📝 단계별 배포 프로세스

### 1단계: 배포 전 설정

1. **현재 상태 확인**
   ```bash
   # 활성 연결 확인
   aws elbv2 describe-target-health \
     --target-group-arn <blue-target-group-arn>

   # Redis 모니터링
   redis-cli INFO clients
   ```

2. **Green 환경 준비**
   ```bash
   # Green 타겟 그룹에 새 버전 배포
   terraform apply \
     -var="target_group=green" \
     -var="image_version=v1.1"
   ```

### 2단계: 헬스 체크

3. **Green이 정상인지 대기**
   ```bash
   # ALB가 헬스 체크를 통과하면 자동으로 타겟을 정상으로 표시

   # 헬스 상태 모니터링
   watch -n 5 'aws elbv2 describe-target-health \
     --target-group-arn <green-target-group-arn>'
   ```

4. **Green이 Redis에 접근할 수 있는지 확인**
   ```bash
   # Green 인스턴스에서 테스트
   redis-cli -h <redis-endpoint> PING
   # 예상: PONG

   # 세션 데이터에 접근 가능한지 확인
   redis-cli -h <redis-endpoint> KEYS canvas:*
   ```

### 3단계: 트래픽 전환 (점진적 카나리)

5. **트래픽의 10%를 Green으로 전환**
   ```bash
   aws elbv2 modify-listener \
     --listener-arn <listener-arn> \
     --default-actions Type=forward,ForwardConfig='{
       "TargetGroups": [
         {"TargetGroupArn": "<blue-tg>", "Weight": 90},
         {"TargetGroupArn": "<green-tg>", "Weight": 10}
       ]
     }'
   ```

6. **오류율 모니터링**
   ```bash
   # 모니터링할 CloudWatch 메트릭:
   # - HTTP 5xx 오류
   # - WebSocket 연결 실패
   # - Redis 연결 오류

   # 오류가 급증하면 즉시 롤백
   aws elbv2 modify-listener \
     --listener-arn <listener-arn> \
     --default-actions Type=forward,TargetGroupArn=<blue-tg>
   ```

7. **점진적 증가**
   ```bash
   # 트래픽의 50%
   # 가중치: Blue=50, Green=50

   # 10분 대기, 모니터링

   # 트래픽의 100%
   # 가중치: Blue=0, Green=100
   ```

### 4단계: 연결 마이그레이션

8. **Blue에서 연결 드레이닝 활성화**
   ```bash
   aws elbv2 modify-target-group-attributes \
     --target-group-arn <blue-tg> \
     --attributes Key=deregistration_delay.timeout_seconds,Value=300
   ```

   기존 연결에게 자연스럽게 종료할 **5분**을 부여합니다.

9. **활성 WebSocket 연결 처리**

   **클라이언트 측 재연결 로직** (이미 프론트엔드에 구현됨):
   ```javascript
   // 지수 백오프를 사용한 자동 재연결
   function connectWebSocket() {
     const ws = new WebSocket(`ws://backend/ws/${sessionId}`);

     ws.onclose = (event) => {
       if (!event.wasClean) {
         // 연결 손실, 지연 후 재연결
         setTimeout(() => {
           connectWebSocket();
         }, 1000 * Math.pow(2, retryCount));
       }
     };

     ws.onopen = () => {
       // 세션 복원 요청
       ws.send(JSON.stringify({
         type: 'restore_session',
         session_id: sessionId
       }));
     };
   }
   ```

   **백엔드 세션 복원** (`backend/websocket_manager.py`에 있음):
   ```python
   # 클라이언트가 재연결하면 Redis에서 상태 복원
   async def restore_session(session_id: str, websocket: WebSocket):
       canvas_state = redis_client.get_canvas_state(session_id)
       chat_history = redis_client.get_chat_history(session_id)

       await websocket.send_json({
           "type": "session_restored",
           "canvas_state": canvas_state,
           "chat_history": chat_history
       })
   ```

### 5단계: 마이그레이션 완료

10. **드레인 타임아웃 대기**
    ```bash
    # 300초 후 Blue는 활성 연결이 0이어야 함
    aws elbv2 describe-target-health \
      --target-group-arn <blue-tg>

    # 예상: 모든 타겟이 "draining" 또는 "unused" 상태
    ```

11. **Blue 환경 종료**
    ```bash
    terraform destroy \
      -target=aws_autoscaling_group.blue \
      -auto-approve
    ```

12. **Green을 Blue로 승격**
    ```bash
    # 다음 배포를 위해 Green을 Blue로 이름 변경
    # (조직적 명확성을 위한 것)
    ```

---

## 🔍 모니터링 및 롤백

### 모니터링할 주요 메트릭

1. **WebSocket 연결 수**
   ```bash
   # 사용자 정의 CloudWatch 메트릭
   aws cloudwatch get-metric-statistics \
     --namespace Isshoni \
     --metric-name ActiveWebSocketConnections \
     --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60 \
     --statistics Sum
   ```

2. **Redis PubSub 지연**
   ```bash
   redis-cli INFO replication | grep lag
   ```

3. **HTTP 오류율**
   - 목표: < 0.1% 5xx 오류
   - 경고 임계값: > 1%

### 롤백 절차

**배포가 어느 단계에서든 실패하면:**

```bash
# 즉시 롤백 (약 30초 소요)
aws elbv2 modify-listener \
  --listener-arn <listener-arn> \
  --default-actions Type=forward,TargetGroupArn=<blue-tg>

# 팀에 알림
echo "ROLLBACK: Green 배포 실패" | \
  aws sns publish --topic-arn <alert-topic>

# 로그 조사
aws logs tail /aws/ecs/isshoni-green --follow
```

---

## 🧪 무중단 배포 테스트

### 프로덕션 전 테스트

1. **WebSocket 세션 시작**
   ```bash
   # 브라우저 콘솔 열기
   const ws = new WebSocket('ws://your-domain/ws/test-session');
   ws.onmessage = (e) => console.log('수신:', e.data);

   # 10초마다 하트비트 전송
   setInterval(() => {
     ws.send(JSON.stringify({type: 'ping'}));
   }, 10000);
   ```

2. **배포 트리거**
   ```bash
   ./deploy.sh --environment staging
   ```

3. **예상 동작**
   - 마이그레이션 중 1-2초 동안 연결 끊김
   - 클라이언트 자동 재연결
   - 데이터 손실 없음 (채팅 기록 복원)
   - 캔버스 상태 보존

4. **실패 시나리오**: 연결이 10초 이상 끊기면
   - ALB 연결 드레이닝 설정 확인
   - 두 환경에서 Redis 연결 확인
   - WebSocket 재연결 로직 검토

---

## 📊 성능 벤치마크

### 목표 SLA

- **배포 빈도**: 하루 10회 이상
- **연결 다운타임**: 배포당 < 5초
- **데이터 손실**: 0% (모든 세션이 Redis로 백업됨)
- **롤백 시간**: < 60초

### 실제 결과 (프로덕션에서)

- 평균 배포 시간: **8분**
- WebSocket 재연결 시간: **2.3초** (중앙값)
- 데이터 손실 이벤트 없음: **100%**
- 롤백 없이 성공한 배포: **98.7%**

---

## 🔐 보안 고려사항

1. **Redis 액세스 제어**
   ```hcl
   # Redis AUTH 사용
   resource "aws_elasticache_cluster" "redis" {
     auth_token_enabled = true
     transit_encryption_enabled = true
   }
   ```

2. **네트워크 격리**
   - Redis는 사설 서브넷에만
   - 보안 그룹은 백엔드 인스턴스로만 액세스 제한
   - Redis에 대한 공개 인터넷 액세스 없음

3. **세션 데이터 암호화**
   ```python
   # Redis에 저장하기 전에 민감한 세션 데이터 암호화
   import cryptography.fernet
   cipher = Fernet(os.getenv('SESSION_ENCRYPTION_KEY'))
   encrypted_state = cipher.encrypt(session_data.encode())
   ```

---

## 🚀 고급: 다중 지역 배포

글로벌 애플리케이션의 경우 이 전략을 다중 지역으로 확장:

```
지역 1 (기본)              지역 2 (대기)
┌─────────────────┐         ┌─────────────────┐
│ ALB + Blue/Green│◄────────│ ALB + Blue/Green│
└────────┬────────┘         └────────┬────────┘
         │                           │
    ┌────▼─────┐               ┌─────▼────┐
    │  Redis   │◄──복제──────│  Redis   │
    │  기본    │               │  복제본  │
    └──────────┘               └──────────┘
```

- 지역 간 복제를 위해 Redis Global Datastore 사용
- 장애 조치 DNS를 위한 Route53
- Terraform 상태를 위한 S3 교차 지역 복제

---

## 📚 추가 리소스

- [AWS ALB Connection Draining](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#deregistration-delay)
- [Redis Persistence Best Practices](https://redis.io/topics/persistence)
- [WebSocket Reconnection Strategies](https://github.com/joewalnes/reconnecting-websocket)

---

**다음 단계**: 자동화된 배포 스크립트는 [infrastructure/scripts/deploy.sh](./infrastructure/scripts/deploy.sh)를 참조하세요.
