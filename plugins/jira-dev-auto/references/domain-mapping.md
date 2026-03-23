# domain-mapping

**목적**: 코드베이스 구조와 티켓 정보를 기반으로 도메인을 분류한다.

## 규칙

### 1. 파일 패턴 → 도메인 매핑 (기본값)
| 파일 경로 패턴 | 도메인 |
|---|---|
| `**/auth/**`, `**/login/**`, `**/session/**` | auth |
| `**/payment/**`, `**/billing/**`, `**/order/**` | payment |
| `**/api/**`, `**/routes/**`, `**/controllers/**` | api |
| `**/user/**`, `**/profile/**`, `**/account/**` | user |
| `**/notification/**`, `**/email/**`, `**/push/**` | notification |
| `**/shared/**`, `**/common/**`, `**/utils/**` | common |

### 2. 티켓 라벨 우선
티켓에 명시적 라벨(`auth`, `payment` 등)이 있으면 파일 패턴보다 우선.

### 3. 컴포넌트 필드 참조
Jira `components` 필드값이 있으면 해당 값을 도메인으로 사용.

### 4. 파일 공유 충돌
두 티켓이 같은 파일을 수정하는 경우:
- **같은 도메인** → 동일 그룹, 순차 실행
- **다른 도메인** → `shared` 도메인으로 이동, 별도 처리

### 5. 병렬화 가능 조건
- `can_parallelize: true`: 수정 대상 파일 겹침 없음 + 도메인 독립
- `can_parallelize: false`: 공유 파일 있음 또는 다른 티켓 의존

### 6. 복잡도 기준
| 기준 | low | medium | high |
|---|---|---|---|
| 수정 파일 수 | 1-3 | 4-8 | 9+ |
| API 변경 | 없음 | 있음 | 브레이킹 |
| DB 스키마 변경 | 없음 | 없음 | 있음 |

## 출력 형식
```yaml
domain: auth
tickets: [PROJ-123, PROJ-124]
can_parallelize: true
complexity: medium
shared_files: []
```
