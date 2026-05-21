---
name: cruise-pr
description: (명시적 커맨드 실행 전용) /cruise:pr 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# PR

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/pr.md` 를 기록하고 [STOP]한다.
> - frontmatter 공통 10필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
> - force push / `--force-with-lease` 일체 사용 안 함
> - 산출물 작성 후 요약·다음 액션 추천 일체 출력하지 않는다 ("완료" 한 줄만)
> - 다른 스킬을 자동으로 호출하지 않는다 (pr 완료 후 review 자동 진입 금지)

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

---

## STEP 2 — 사전 검증

1. 미푸시 커밋 점검:
   ```bash
   git log @{upstream}..HEAD --oneline 2>/dev/null || git log origin/{base_branch}..HEAD --oneline
   ```
2. base 대비 커밋 50개 초과 시 `AskUserQuestion` 경고 게이트:
   - "커밋이 {n}개입니다. PR을 계속 생성할까요?" (계속/취소)
   - 취소 → status=cancelled 로 pr.md 기록 후 [STOP]

---

## STEP 3 — assignee 확인

```bash
gh api user -q .login
```

결과를 `my_login` 으로 저장.

---

## STEP 4 — 라벨 추론

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/infer_labels.py \
  {root} {base_branch}
```

`data.labels[]` 확보.

---

## STEP 5 — PR 컨텐츠 준비

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/prepare_pr.py \
  {root} {base_branch} {branch}
```

`commits`, `stats`, `major_areas`, `suggested_type`, `suggested_scope`, `issue_keys` 확보.

---

## STEP 6 — 제목·본문 생성

`templates/pr-title.md` 와 `templates/pr-body.md` 형식을 사용해 PR 제목과 본문 작성.
`~/Documents/tasks/{KEY}/task.md` 가 있으면 완료 조건 섹션을 PR 체크리스트로 포함.

---

## STEP 7 — [GATE] PR 내용 확인

`AskUserQuestion`: "이 내용으로 PR을 생성할까요?"

표시:
- 제목: `{title}`
- base 브랜치: `{base_branch}`
- 라벨: `{labels}`
- assignee: `{my_login}`
- 본문 요약 (첫 200자)

**확인** → STEP 8
**수정** → 사용자 지시대로 갱신 → STEP 7 반복
**취소** → status=cancelled 로 pr.md 기록 후 [STOP]

---

## STEP 8 — Push

```bash
git push -u origin HEAD
```

실패 (non-ff 등):
- force 일체 사용하지 않음
- status=failed 로 pr.md 기록 후 [STOP]

---

## STEP 9 — PR 생성

```bash
gh pr create \
  --base {base_branch} \
  --assignee {my_login} \
  --title "{title}" \
  --body-file /tmp/cruise_pr_body.md \
  {--label label1 --label label2 ...}
```

- 성공: pr.md 작성 (`pr_url` 포함), status=completed
- "already exists" 오류: `gh pr list --head {branch} --json url -q '.[0].url'` 로 기존 URL 조회 → 동일하게 기록
- 그 외 실패: status=failed 로 pr.md 기록 후 [STOP]

---

## STEP 10 — pr.md 저장

frontmatter (공통 10필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: pr
summary: {task.md에서 상속, 없으면 ""}
branch: {branch}
repo: {repo}
head_sha: {git rev-parse --short HEAD}
status: completed
created: {UTC ISO8601}
updated: {UTC ISO8601}
tags: []
pr_url: "https://github.com/{repo}/pull/{n}"
pr_number: {n}
base_branch: {base_branch}
labels:
  - {label}
assignee: {my_login}
---
```

본문:
- `# PR — {KEY}` (H1)
- `## 제목` — PR 제목
- `## 본문` — PR 본문 (요약)
- `## 메타` — labels, assignee, base

"완료" 한 줄 출력 후 [STOP].
