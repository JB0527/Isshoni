# Isshoni - 상세 아키텍처 문서

## 🏗 시스템 아키텍처

### 고수준 개요

```
┌──────────────────────────────────────────────────────────────────┐
│                          인터넷                                   │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                ┌───────────▼────────────┐
                │  Route53 (DNS)         │
                │  + CloudFront (CDN)    │
                └───────────┬────────────┘
                            │
                ┌───────────▼────────────┐
                │  Application Load      │
                │  Balancer (ALB)        │
                │  - SSL 종료            │
                │  - 헬스 체크           │
                └───────────┬────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼─────────┐                   ┌─────────▼───────┐
│ Blue 환경       │                   │Green 환경       │
│ (v1.0)          │                   │ (v1.1)          │
│                 │                   │                 │
│ ┌─────────────┐ │                   │ ┌─────────────┐ │
│ │  프론트엔드  │ │                   │ │  프론트엔드  │ │
│ │ (Streamlit) │ │                   │ │ (Streamlit) │ │
│ └──────┬──────┘ │                   │ └──────┬──────┘ │
│        │        │                   │        │        │
│ ┌──────▼──────┐ │                   │ ┌──────▼──────┐ │
│ │   백엔드    │ │                   │ │   백엔드    │ │
│ │  (FastAPI)  │ │                   │ │  (FastAPI)  │ │
│ │  WebSocket  │ │                   │ │  WebSocket  │ │
│ └──────┬──────┘ │                   │ └──────┬──────┘ │
└────────┼────────┘                   └────────┼────────┘
         │                                     │
         └──────────────┬──────────────────────┘
                        │
        ┌───────────────┴───────────────────────────┐
        │                                           │
        │         공유 인프라                        │
        │                                           │
┌───────▼──────┐  ┌──────────────┐  ┌──────────────┐
│   Redis      │  │  S3 버킷     │  │ CloudWatch   │
│  클러스터    │  │ (TF State)   │  │  (로그)      │
│              │  │              │  │              │
│ - 세션       │  │ - 상태       │  │ - 메트릭     │
│ - PubSub     │  │ - 백업       │  │ - 알람       │
│ - 캐시       │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │
        │
┌───────▼────────────────────────────────────────────┐
│              외부 서비스                            │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Anthropic    │  │   SSAFY GMS  │  │   AWS    │ │
│  │   Claude     │  │    GPT-5     │  │ Services │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 📦 컴포넌트 상세

### 1. 프론트엔드 레이어 (Streamlit)

**기술**: Streamlit 1.31.0

**책임**:
- 인프라 드래그 앤 드롭 설계를 위한 비주얼 캔버스
- 실시간 협업 채팅 UI
- 코드 미리보기 및 다운로드
- 배포 컨트롤

**주요 파일**:
- `frontend/app.py` - 메인 애플리케이션 진입점
- `frontend/canvas.py` - 비주얼 캔버스 컴포넌트 (향후 개선)
- `frontend/chat.py` - 실시간 채팅 UI (향후 개선)

**통신**:
- CRUD 작업을 위한 백엔드로의 HTTP REST API 호출
- 실시간 업데이트를 위한 WebSocket 연결
- 배포 상태를 위한 서버 전송 이벤트

**상태 관리**:
```python
# Streamlit 세션 상태
st.session_state = {
    'session_id': UUID,
    'user_id': str,
    'username': str,
    'canvas_resources': List[Dict],
    'canvas_connections': List[Dict],
    'generated_code': str,
    'chat_messages': List[Dict]
}
```

---

### 2. 백엔드 레이어 (FastAPI)

**기술**: FastAPI + Uvicorn

**엔드포인트**:

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| GET | `/` | 헬스 체크 |
| GET | `/api/sessions/{id}/canvas` | 캔버스 상태 가져오기 |
| POST | `/api/sessions/{id}/canvas` | 캔버스 업데이트 |
| GET | `/api/sessions/{id}/chat` | 채팅 기록 가져오기 |
| POST | `/api/sessions/{id}/chat` | 채팅 메시지 전송 |
| POST | `/api/generate-code` | AI로 IaC 코드 생성 |
| POST | `/api/deploy` | 인프라 배포 |
| WS | `/ws/{session_id}` | 실시간 동기화를 위한 WebSocket |

**WebSocket 메시지 타입**:
```json
{
  "type": "canvas_update",
  "data": { "resources": [...], "connections": [...] }
}

{
  "type": "chat_message",
  "data": { "username": "user1", "message": "..." }
}

{
  "type": "user_connected",
  "active_users": 3
}
```

**핵심 컴포넌트**:

1. **WebSocket 관리자** (`websocket_manager.py`)
   - 세션별 활성 연결 관리
   - 세션의 모든 클라이언트에게 업데이트 브로드캐스트
   - 연결 해제를 우아하게 처리

2. **Redis 클라이언트** (`redis_client.py`)
   - 세션 지속성
   - 캔버스 상태 저장 (TTL: 24시간)
   - 채팅 기록 (Redis Streams, 최대 1000개 메시지)
   - 인스턴스 간 통신을 위한 PubSub

3. **AI 생성기** (`ai_generator.py`)
   - 인프라 요구사항을 위한 프롬프트 엔지니어링
   - Claude 3.5 Sonnet 및 GPT-5와의 통합
   - 템플릿 기반 코드 생성

4. **Terraform 실행기** (`terraform_executor.py`)
   - 프로그래매틱하게 Terraform 명령 실행
   - 임시 작업 디렉토리 관리
   - 출력 캡처 및 반환

---

### 3. 데이터 레이어 (Redis)

**기술**: AWS ElastiCache for Redis 7.0

**데이터 구조**:

1. **캔버스 상태** (String, JSON 인코딩)
   ```
   Key: canvas:{session_id}
   TTL: 86400초 (24시간)
   Value: {
     session_id, resources[], connections[], user_prompt, last_updated
   }
   ```

2. **채팅 기록** (Stream)
   ```
   Key: chat:{session_id}
   최대 길이: 1000개 메시지
   Fields: user_id, username, message, timestamp
   ```

3. **활성 세션** (Set)
   ```
   Key: active_sessions
   Members: session_id1, session_id2, ...
   ```

4. **PubSub 채널**
   ```
   Channel: canvas_updates:{session_id}
   Channel: chat_updates:{session_id}
   ```

**성능 튜닝**:
- `maxmemory-policy`: allkeys-lru (최소 최근 사용 제거)
- `timeout`: 300초
- 지속성: 내구성을 위한 AOF (Append-Only File)

---

### 4. AI 통합

**지원하는 제공자**:

1. **Anthropic Claude 3.5 Sonnet**
   - 모델: `claude-3-5-sonnet-20241022`
   - 최대 토큰: 4096
   - 최적: 상세한 주석이 있는 복잡한 인프라

2. **SSAFY GMS GPT-5**
   - 모델: `gpt-5`
   - 최대 토큰: 128000
   - 컨텍스트: 400k 토큰
   - 최적: 대규모 인프라 패턴

**프롬프트 엔지니어링 전략**:

```
시스템 프롬프트:
"당신은 전문 AWS 인프라 설계자입니다..."

사용자 프롬프트 =
  [사용자 설명] +
  [캔버스 리소스 목록] +
  [리소스 간 연결] +
  [모범 사례 요구사항]

출력 제약:
- Terraform/CloudFormation 코드만
- 마크다운 포맷팅 없음
- 주석 포함
- 구성 가능한 매개변수를 위한 변수 사용
```

**비용 최적화**:
- 일반적인 패턴을 캐시하여 API 호출 감소
- 간단한 요청에는 저렴한 모델 사용
- 여러 작은 요청을 배치 처리

---

### 5. 인프라 배포

**Terraform 워크플로우**:

1. **코드 생성** (AI)
   ```
   캔버스 → 프롬프트 → LLM → Terraform 코드
   ```

2. **검증**
   ```bash
   terraform init
   terraform validate
   terraform plan
   ```

3. **배포**
   ```bash
   terraform apply -auto-approve
   ```

4. **상태 관리**
   - 버전 관리와 함께 S3에 저장
   - 동시 변경 방지를 위한 DynamoDB 상태 잠금
   - 저장 시 암호화

**보안**:
- AWS 자격 증명은 백엔드에 절대 저장되지 않음
- 환경 변수를 통해 전달
- Terraform 작업은 격리된 컨테이너에서 실행
- 최소 권한 액세스를 가진 IAM 역할

---

## 🔄 데이터 흐름 예시

### 예시 1: 사용자가 캔버스에 리소스 추가

```
[사용자 브라우저]
    │ (1) "EC2 추가" 클릭
    ├──► [프론트엔드: Streamlit]
           │ (2) 로컬 상태 업데이트
           │     st.session_state.canvas_resources.append(...)
           │
           │ (3) WebSocket으로 전송
           ├──► [백엔드: WebSocket 핸들러]
                  │ (4) Redis에 저장
                  ├──► [Redis: canvas:{session_id}]
                  │
                  │ (5) 모든 클라이언트에게 브로드캐스트
                  ├──► [WebSocket 관리자]
                         │
                         ├──► [사용자 A 브라우저] ← 업데이트
                         ├──► [사용자 B 브라우저] ← 업데이트
                         └──► [사용자 C 브라우저] ← 업데이트
```

### 예시 2: 인프라 코드 생성

```
[사용자 브라우저]
    │ (1) "코드 생성" 클릭
    ├──► [프론트엔드: HTTP POST /api/generate-code]
           │
           ├──► [백엔드: AI 생성기]
                  │ (2) 프롬프트 구축
                  │     - 사용자 설명: "재난 알림 시스템"
                  │     - 리소스: [ALB, EC2, RDS, Redis]
                  │     - 연결: [ALB→EC2, EC2→RDS, EC2→Redis]
                  │
                  │ (3) AI API 호출
                  ├──► [Anthropic/SSAFY GMS]
                         │
                         │ (4) Terraform 코드 반환
                         └──► [백엔드]
                                │ (5) 프론트엔드로 전송
                                └──► [사용자 브라우저]
                                       │ 코드 에디터에 표시
                                       │ 다운로드 버튼 활성화
```

### 예시 3: 인프라 배포

```
[사용자 브라우저]
    │ (1) "배포" 클릭
    ├──► [백엔드: Terraform 실행기]
           │ (2) 임시 디렉토리 생성
           │     /tmp/terraform_{session_id}/
           │
           │ (3) main.tf에 코드 작성
           │
           │ (4) terraform init 실행
           ├──► [Terraform CLI]
                  │
                  │ (5) 프로바이더 다운로드
                  │
           │ (6) terraform apply 실행
           ├──► [AWS API]
                  │
                  │ (7) 리소스 생성
                  │     - VPC
                  │     - 서브넷
                  │     - EC2 인스턴스
                  │     - RDS 데이터베이스
                  │     - ...
                  │
                  │ (8) 리소스 ID 반환
                  └──► [백엔드]
                         │ (9) S3에 상태 저장
                         ├──► [S3: terraform.tfstate]
                         │
                         │ (10) 출력 반환
                         └──► [프론트엔드]
                                │ 성공 표시
                                │ 리소스 URL 표시
```

---

## 🚀 확장성 아키텍처

### 수평 확장

**백엔드 Auto Scaling**:
```
최소 인스턴스: 2
최대 인스턴스: 20
목표 CPU: 70%
목표 메모리: 80%
```

**과제 및 해결책**:

1. **WebSocket 연결**
   - 문제: 고정 세션 필요, 로드 밸런싱 제한
   - 해결: 세션 친화성(고정 쿠키)을 사용하는 ALB

2. **상태 동기화**
   - 문제: 여러 백엔드 인스턴스가 공유 상태 필요
   - 해결: 단일 진실 공급원으로서의 Redis

3. **메시지 브로드캐스팅**
   - 문제: WebSocket 메시지가 모든 인스턴스에 도달해야 함
   - 해결: 인스턴스 간 통신을 위한 Redis PubSub

### 수직 확장

**리소스 할당**:
```
프론트엔드: t3.medium (2 vCPU, 4GB RAM)
백엔드:     t3.large (2 vCPU, 8GB RAM)
Redis:      cache.m5.large (2 vCPU, 6.4GB RAM)
```

**데이터베이스 크기 조정**:
- 10,000개 동시 세션 → ~100MB Redis 메모리
- 초당 1,000개 메시지 → Redis는 초당 100k 작업 처리 가능

---

## 🔐 보안 모델

### 인증 및 권한 부여

**현재 (MVP)**:
- 인증 없음 (신뢰 기반)
- 세션 ID는 UUID (추측하기 어려움)

**향후 개선**:
- OAuth 2.0 통합 (Google, GitHub)
- API 액세스를 위한 JWT 토큰
- RBAC (역할 기반 액세스 제어)

### 데이터 보호

1. **전송 중**:
   - ALB → 백엔드: HTTPS (TLS 1.3)
   - 백엔드 → Redis: TLS 암호화
   - 백엔드 → AWS API: HTTPS

2. **저장 시**:
   - Redis: 저장 시 암호화 활성화
   - S3 (Terraform 상태): AES-256 암호화
   - 시크릿: AWS Secrets Manager

3. **네트워크 격리**:
   ```
   공개 서브넷:   ALB만
   사설 서브넷:   백엔드, Redis, RDS
   인그레스 없음: 보안 그룹에 의해 0.0.0.0/0 차단
   ```

### 입력 검증

**인젝션 공격 방지**:
```python
# Terraform 코드 검증
def validate_terraform_code(code: str) -> bool:
    # 악의적인 명령 확인
    dangerous_patterns = [
        r'rm\s+-rf',
        r'curl.*\|.*bash',
        r'eval\(',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            raise SecurityException("위험한 패턴 감지")
```

---

## 📊 모니터링 및 관찰성

### 메트릭

**애플리케이션 메트릭** (CloudWatch 사용자 정의 메트릭):
- 활성 WebSocket 연결
- 초당 캔버스 업데이트
- AI 코드 생성 요청
- 배포 성공률
- 평균 배포 시간

**인프라 메트릭** (CloudWatch):
- ALB 요청 수
- ALB 5xx 오류
- EC2 CPU/메모리 사용률
- Redis 연결
- Redis 메모리 사용량

### 로깅

**로그 집계**:
```
백엔드 → CloudWatch Logs → 로그 그룹
  - /aws/ecs/isshoni-backend
  - /aws/ecs/isshoni-frontend

형식: JSON 구조화 로깅
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "service": "backend",
  "session_id": "abc-123",
  "message": "코드 생성 성공",
  "duration_ms": 2341
}
```

### 알림

**긴급 알림** (SNS → 이메일/Slack):
- 5xx 오류율 > 1%
- WebSocket 연결 실패 > 5%
- Redis 연결 오류
- 배포 실패

**경고 알림**:
- CPU 사용량 > 80%
- 메모리 사용량 > 85%
- 디스크 사용량 > 90%

---

## 🔄 재해 복구

### 백업 전략

1. **Redis**:
   - 6시간마다 자동 스냅샷
   - 보존 기간: 7일
   - 시점 복구 가능

2. **Terraform 상태**:
   - S3 버전 관리 활성화
   - us-west-2로 교차 지역 복제
   - 수명 주기 정책: 30개 버전 유지

3. **데이터베이스** (향후):
   - RDS 자동 백업
   - 다중 AZ 배포
   - 고가용성을 위한 읽기 복제본

### 복구 시간 목표 (RTO)

- **서비스 중단**: 5분 (대기 지역으로 장애 조치)
- **데이터 손실 (RPO)**: < 1시간 (Redis 스냅샷 빈도)
- **전체 지역 장애**: 30분 (수동 DR 호출)

---

## 🚧 향후 개선 사항

### Phase 2 (2025년 2분기)

1. **VSCode 확장**
   - AWS Toolkit과의 직접 통합
   - 캔버스 편집을 위한 Live Share
   - 일반적인 패턴을 위한 코드 스니펫

2. **비용 추정**
   - 실시간 비용 계산기
   - 월별 비용 예측
   - 비용 최적화 제안

3. **규정 준수 검사**
   - CIS AWS Foundations Benchmark
   - HIPAA 규정 준수 검증
   - PCI-DSS 검사

### Phase 3 (2025년 3분기)

1. **멀티 클라우드 지원**
   - Azure Resource Manager
   - Google Cloud Deployment Manager
   - 통합 추상화 계층

2. **인프라 Git**
   - 인프라 버전 관리
   - 차이점 시각화
   - 이전 버전으로 롤백

3. **마켓플레이스**
   - 사전 제작된 템플릿
   - 커뮤니티 기여
   - 검증된 패턴

---

**최종 업데이트**: 2025-01-15
**버전**: 1.0.0
**유지 관리자**: Isshoni 팀
