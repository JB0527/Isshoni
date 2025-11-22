# Isshoni - AI 기반 비주얼 클라우드 인프라 생성기

> "一緒に (Isshoni)" = 함께 (일본어) - AI와 함께 클라우드 인프라 구축하기
>
> **소프트뱅크 클라우드 대회** 출품작

## 🚀 개요

Isshoni는 **No-Code/Low-Code AI 기반 인프라 설계 및 배포 플랫폼**으로, 팀이 비주얼 드래그 앤 드롭 인터페이스를 통해 협업하며 AWS 인프라를 설계, 생성 및 배포할 수 있도록 합니다.

### 주요 기능

- **비주얼 인프라 디자이너**: AWS 서비스 아이콘을 드래그 앤 드롭하여 아키텍처 설계
- **실시간 협업**: WebSocket 기반 실시간 편집 및 팀 채팅
- **AI 코드 생성**: 디자인으로부터 CloudFormation/Terraform 코드 자동 생성
- **원클릭 배포**: 단 한 번의 클릭으로 AWS에 인프라 직접 배포
- **VSCode 통합**: 원활한 개발 경험을 위한 AWS Toolkit 통합

---

## 🏗 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                  프론트엔드 (Streamlit)                       │
│  - 비주얼 캔버스 (드래그 앤 드롭)                            │
│  - 실시간 채팅 UI                                           │
│  - 코드 미리보기 & 배포 버튼                                 │
└───────────────────┬─────────────────────────────────────────┘
                    │ WebSocket + REST API
┌───────────────────▼─────────────────────────────────────────┐
│           백엔드 (FastAPI + WebSocket)                       │
│  - 세션 관리                                                │
│  - 캔버스 상태 동기화                                        │
│  - AI 프롬프트 엔지니어링                                    │
│  - Terraform/CloudFormation 실행기                          │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴──────────┬──────────────────┐
        ▼                      ▼                  ▼
  ┌──────────┐         ┌──────────────┐    ┌──────────────┐
  │   LLM    │         │    Redis     │    │  S3 버킷     │
  │ (GPT-5/  │         │ (세션 &      │    │ (Terraform   │
  │  Claude) │         │  PubSub)     │    │   State)     │
  └──────────┘         └──────────────┘    └──────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │   AWS 클라우드   │
                                          │ (VPC, EC2, RDS) │
                                          └─────────────────┘
```

---

## 📁 프로젝트 구조

```
Isshoni/
├── README.md                           # 이 파일
├── ARCHITECTURE.md                     # 상세 아키텍처 설계
├── DEPLOYMENT_GUIDE.md                 # Blue-Green 배포 전략
│
├── backend/
│   ├── main.py                         # FastAPI 진입점
│   ├── websocket_manager.py            # WebSocket 연결 관리자
│   ├── ai_generator.py                 # AI 프롬프트 엔지니어링 및 코드 생성
│   ├── terraform_executor.py           # Terraform apply/destroy 로직
│   ├── cloudformation_executor.py      # CloudFormation 배포 로직
│   ├── models.py                       # Pydantic 데이터 모델
│   ├── redis_client.py                 # Redis PubSub (채팅 및 상태용)
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app.py                          # Streamlit 메인 UI
│   ├── canvas.py                       # 비주얼 드래그 앤 드롭 캔버스
│   ├── chat.py                         # 실시간 채팅 컴포넌트
│   ├── requirements.txt
│   └── Dockerfile
│
├── templates/                          # 사전 제작된 IaC 템플릿
│   ├── vpc_basic.tf
│   ├── alb_autoscaling.tf
│   ├── redis_cluster.tf
│   ├── disaster_notification.yaml      # 예시: 재난 알림 시스템
│   └── README.md
│
├── infrastructure/                     # 프로덕션 인프라
│   ├── terraform/
│   │   ├── main.tf                    # Isshoni 플랫폼 인프라
│   │   ├── blue_green.tf              # Blue-Green 배포 설정
│   │   └── README.md
│   └── scripts/
│       ├── deploy.sh
│       └── rollback.sh
│
├── docker-compose.yml                  # 로컬 개발 환경
└── .env.example                        # 환경 변수 템플릿
```

---

## 🔧 기술 스택

### 백엔드
- **FastAPI**: WebSocket 지원 비동기 웹 프레임워크
- **Redis**: 세션 관리, 실시간 채팅용 PubSub, 캔버스 상태 캐시
- **Boto3**: Python용 AWS SDK (CloudFormation, S3, EC2 API)
- **Python Terraform**: 프로그래매틱 실행을 위한 Terraform 래퍼
- **Anthropic/OpenAI SDK**: AI 코드 생성 (Claude 3.5 Sonnet 또는 GPT-5)

### 프론트엔드
- **Streamlit**: UI 빠른 프로토타이핑 (나중에 React로 교체 가능)
- **Streamlit-Drawable-Canvas**: 비주얼 드래그 앤 드롭 인터페이스
- **WebSocket Client**: 실시간 협업

### 인프라
- **Terraform**: 주요 IaC 도구
- **AWS CloudFormation**: 대체 IaC 지원
- **AWS S3**: Terraform 원격 상태 저장소
- **AWS ALB + Auto Scaling**: 백엔드 고가용성
- **AWS ElastiCache (Redis)**: 배포 간 세션 지속성

---

## 🚦 핵심 워크플로우

### 1. 사용자 여정: 설계에서 배포까지

```
사용자 입력
   │
   ├─► "재난 알림 시스템을 만들고 싶어요"
   │
   ▼
비주얼 캔버스
   │
   ├─► 드래그 앤 드롭: [ALB] -> [EC2 Auto Scaling] -> [RDS]
   ├─► 메모 추가: "WebSocket 세션 지속성을 위해 Redis 사용"
   │
   ▼
AI 처리
   │
   ├─► 캔버스 JSON 파싱: { resources: [...], connections: [...] }
   ├─► 사용자 메모 + 아키텍처 패턴 결합
   ├─► 프롬프트 생성: "다음을 위한 Terraform 코드 생성..."
   │
   ▼
코드 생성
   │
   ├─► LLM이 완전한 Terraform/CloudFormation 코드 반환
   ├─► 사용자가 미리보기 패널에서 코드 검토
   │
   ▼
배포
   │
   ├─► terraform init && terraform apply
   ├─► AWS에서 리소스 생성
   ├─► 상태를 S3에 저장
   │
   ▼
완료!
```

### 2. 실시간 협업 흐름

```
사용자 A: 캔버스에 EC2 추가
   │
   ├─► WebSocket → 백엔드 → Redis PubSub
   │
   ▼
사용자 B: 실시간으로 EC2 표시 확인
   │
   ├─► 사용자 B가 RDS 추가하고 EC2와 연결
   │
   ▼
사용자 A & B: 데이터베이스 설정에 대해 채팅
   │
   ├─► 채팅 메시지를 Redis Streams에 저장
   │
   ▼
AI: 더 스마트한 코드 생성을 위해 채팅 컨텍스트 읽기
```

---

## 🛡 고가용성 및 무중단 설계

### 과제: 배포 중 WebSocket 연결

**문제**: 전통적인 blue-green 배포는 활성 WebSocket 연결을 중단시킵니다.

**해결책**: Redis 기반 세션 지속성 + 연결 마이그레이션

```
┌──────────────────────────────────────────────────────────┐
│  1단계: Green 환경 시작 (새 버전)                         │
│  - 백엔드 v2가 동일한 Redis 클러스터에 연결               │
│  - Redis에서 활성 세션 읽기                              │
└───────────────────┬──────────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────────┐
│  2단계: ALB가 점진적으로 트래픽 전환 (0% → 100%)          │
│  - 새 연결 → Green (v2)                                  │
│  - 기존 연결 → Blue (v1) 자연스럽게 종료될 때까지         │
└───────────────────┬──────────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────────┐
│  3단계: 세션 인계 (중요한 연결용)                         │
│  - 클라이언트 재연결 → Green이 Redis에서 세션 읽기        │
│  - 채팅 기록 보존                                        │
│  - 캔버스 상태 복원                                      │
└───────────────────┬──────────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────────┐
│  4단계: 드레인 타임아웃 후 Blue 종료 (300초)              │
│  - 모든 연결 마이그레이션 완료                            │
│  - Blue 환경 종료                                        │
└──────────────────────────────────────────────────────────┘
```

**핵심 기술**:
- **Redis Keyspace Notifications**: 세션 업데이트 감지
- **ALB Connection Draining**: 우아한 종료를 위한 300초 타임아웃
- **WebSocket 재연결 로직**: 클라이언트가 세션 ID로 자동 재연결

자세한 구현은 [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)를 참조하세요.

---

## 🚀 빠른 시작

### 사전 요구사항

- Docker & Docker Compose
- AWS 계정 (프로그래매틱 액세스 포함)
- SSAFY GMS API Key 또는 Anthropic API Key

### 로컬 개발

1. **복제 및 설정**
```bash
git clone <repo-url>
cd Isshoni
cp .env.example .env
# 자격 증명으로 .env 편집
```

2. **서비스 시작**
```bash
docker-compose up -d
```

3. **애플리케이션 접속**
- 프론트엔드: http://localhost:8501
- 백엔드 API: http://localhost:8000
- API 문서: http://localhost:8000/docs

### 환경 변수

```env
# AWS 자격 증명
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-northeast-2

# AI 제공자 (하나 선택)
ANTHROPIC_API_KEY=sk-ant-xxxxx
# 또는
OPENAI_API_KEY=your_gms_api_key  # SSAFY GMS GPT-5

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Terraform State용 S3
TERRAFORM_STATE_BUCKET=isshoni-tfstate-bucket
```

---

## 🎯 로드맵

### Phase 1: MVP (현재)
- [x] 드래그 앤 드롭 기본 캔버스
- [x] WebSocket 실시간 동기화
- [x] AI Terraform 생성
- [x] 원클릭 배포

### Phase 2: 향상된 협업
- [ ] AWS Toolkit 통합 VSCode 확장
- [ ] 멀티 커서 편집 (Figma처럼)
- [ ] 인프라용 버전 관리 (Git 스타일)
- [ ] 팀 권한 및 RBAC

### Phase 3: 엔터프라이즈 기능
- [ ] 배포 전 비용 추정
- [ ] 규정 준수 검사 (CIS 벤치마크)
- [ ] 멀티 클라우드 지원 (Azure, GCP)
- [ ] 실패 시 자동 롤백

---

## 🤝 기여

오픈소스 프로젝트입니다. 기여를 환영합니다!

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 열기

---

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일 참조

---

## 🙏 감사의 말

- Brainboard, Eraser.io, Terraform Cloud와 같은 도구에서 영감을 받았습니다
- YAML이 아닌 아키텍처에 집중하고 싶은 DevOps 엔지니어를 위해 제작되었습니다

---

**Anthropic의 Claude Code로 제작**
