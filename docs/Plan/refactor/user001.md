1. 현황 파악 및 시각화 도구 (진단용)
먼저 엉켜있는 참조 관계(import dependency)를 눈으로 확인해야 분리가 가능합니다.

1) Pydeps (Dependency Graph Generator)

역할: Python 파일 간의 import 관계를 분석하여 방향성 그래프(Directed Graph)로 그려줍니다.

사용 목적:

"누가 누구를 참조하는가?"를 팩트로 확인.

순환 참조(Circular Dependency) 구간 발견.

계층을 위반한 import(예: 도메인 로직이 UI를 import 하는 경우) 식별.

명령어: pydeps my_project --graph-output dot

2) SonarQube / SonarLint

역할: 정적 코드 분석 도구.

사용 목적:

코드 복잡도(Cyclomatic Complexity)가 지나치게 높은 파일 식별.

"God Class"(너무 많은 책임을 가진 클래스) 탐지 -> 파일 분리의 기준점이 됨.

2. 계층 구조 정책 강제 도구 (경찰 역할)
"앞으로 이 폴더는 저 폴더를 import 하면 안 돼"라는 정책을 머리로만 생각하면 무조건 깨집니다. 이를 CI/CD나 로컬 테스트 단계에서 에러로 뱉어내는 툴이 필요합니다.

1) Import Linter

핵심 기능: 프로젝트의 계층 구조 규칙(Contract)을 정의하고, 이를 위반하는 import 문이 발견되면 에러를 발생시킵니다.

설정 예시 (.importlinter 파일):

Ini, TOML

[importlinter]
root_package = my_project

[importlinter:contract:layers]
name = Layered Architecture Policy
type = layers
layers =
    presentation  # 최상위
    service       # 중간
    domain        # 핵심 (여기는 위쪽을 절대 import 못함)
    infrastructure
효과: domain 폴더에 있는 파일이 service 폴더를 import 하려고 하면, 이 툴이 차단합니다. 파일 위치를 정할 때 강력한 가이드라인이 됩니다.

3. DI 및 객체 수명 관리 도구 (IoC Container)
질문하신 "Singleton 패턴 없이 Injection 하기", **"이미 존재하는 인스턴스 재사용(중복 방지)"**를 해결하려면 **DI 프레임워크(IoC Container)**를 도입하는 것이 가장 확실합니다.

Python에서는 Dependency Injector 라이브러리가 사실상의 표준(De facto standard)입니다.

Tool: Dependency Injector

역할: 객체의 생성, 주입, 수명 관리(Scope)를 전담하는 **'컨테이너(Container)'**를 제공합니다.

질문하신 문제 해결 방식:

Q1. Singleton 없이 Injection?

이 라이브러리는 전역 변수(Global state)로서의 싱글톤 패턴을 쓰지 않습니다.

대신 **컨테이너 내부에서만 유지되는 'Singleton Scope'**를 제공합니다. 앱이 종료되면 깔끔하게 사라지며, 테스트 시에는 Mock으로 갈아끼우기 쉽습니다.

Q2. 이미 존재하는 Class 중복 없이 활용?

providers.Singleton을 사용하면, 컨테이너가 **최초 1회만 객체를 생성(Memory 0x1000 할당)**하고, 그 이후에 누가 요청하든 이미 생성된 0x1000 주소값만 계속 던져줍니다.

providers.Factory를 사용하면 요청할 때마다 new를 해서 새로운 주소값을 던져줍니다.

이걸 설정 파일(Container)에서 한눈에 관리합니다.

Q3. 코드를 어느 파일에 편입시킬 것인가?

이 툴을 쓰면 구조가 강제됩니다.

containers.py: 객체 조립 명세서 (모든 주입 규칙이 여기 모임)

services.py: 비즈니스 로직 (받아서 쓰는 놈)

repositories.py: DB 접근 (실제 데이터)

[코드 예시: Dependency Injector 적용]

Python

from dependency_injector import containers, providers

# [설계도] 객체들의 관계와 수명을 정의하는 파일 (containers.py)
class Container(containers.DeclarativeContainer):
    
    # 1. Configuration (설정 주입)
    config = providers.Configuration()

    # 2. Database (싱글톤 스코프: 앱 실행 중 딱 1번만 연결)
    # 질문하신 "중복 없이 기존 코드 활용"이 여기서 보장됨.
    db_client = providers.Singleton(
        DatabaseClient,
        url=config.db.url
    )

    # 3. Service (주입)
    # UserLogic을 만들 때, 위에서 만든 db_client(이미 있는 놈)를 
    # 자동으로 __init__에 꽂아 넣어라.
    user_logic = providers.Factory(
        UserLogic,
        db=db_client  # <--- Dependency Injection
    )
4. 파일/폴더 구조화 가이드 (표준 아키텍처)
새 파일을 어디에 만들지 고민될 때는 '클린 아키텍처' 혹은 **'헥사고날 아키텍처'**의 디렉토리 구조를 따르는 것이 좋습니다.

추천 폴더 구조:

Plaintext

my_project/
├── domain/            # [순수 로직] 외부 라이브러리 의존성 0%. 데이터 모델(Entity) 등.
├── application/       # [유스케이스] 실제 비즈니스 흐름. (예: 주식 매수 절차)
│   └── services.py    # 여기에 로직 위치
├── infrastructure/    # [외부 연동] DB, API 클라이언트, 로그 파일 등 구체적 기술.
│   └── kiwoom_api.py  # 주식 서버 연동 코드
├── presentation/      # [진입점] main.py, API 서버 엔드포인트 등.
└── containers.py      # [조립 공장] 위 3개의 계층을 Import해서 '연결'만 시켜주는 곳.
요약 및 제안
진단: Pydeps로 현재 스파게티 상태를 그래프로 뽑아봅니다. (순환 참조 고리 끊기가 1순위)

정책: Import Linter를 설치하여 domain 폴더가 infrastructure를 import 하지 못하도록 설정 파일에 박아버립니다.

구현: Dependency Injector 라이브러리를 설치합니다.

containers.py 파일을 하나 만듭니다.

여기에 providers.Singleton을 이용해 DB나 API 클라이언트처럼 **'하나만 있어야 하는 객체'**를 등록합니다.

필요한 곳에 이 provider들을 인자로 넘겨주도록 설정하면, 직접 getInstance()를 호출할 필요 없이 깔끔하게 주소값이 공유됩니다.