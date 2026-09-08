# U02 요약 — Auth 보안 옵션 설정

## 1. 완료한 것

Supabase 대시보드(`borigunbbang's Project`) → Authentication에서 설정:

- **Confirm email**: ON (Authentication → Sign In / Providers → User Signups)
  - 가입 시 이메일 확인 전에는 로그인 불가
  - 발송 메일은 아직 **Supabase 기본 내장 메일러**(커스텀 SMTP 미연결) — 발송량 제한이 있어 실사용 전 반드시 교체 필요
- **비밀번호 정책**: Authentication → Sign In / Providers → Email 설정 패널
  - Minimum password length: `6` → `8`로 변경
  - Password requirements: `No required characters` → `Lowercase, uppercase letters and digits`로 변경
  - 저장 완료("Successfully updated settings" 확인)

## 2. 완료 기준 테스트 결과

`curl`로 Supabase Auth signup API 직접 호출해서 확인:

1. 약한 비밀번호 거부 테스트
   ```
   POST /auth/v1/signup {"email":"weak-pw-test-u02@example.com","password":"abc123"}
   → 422 weak_password
     "Password should be at least 8 characters. Password should contain at least one
      character of each: abcdefghijklmnopqrstuvwxyz, ABCDEFGHIJKLMNOPQRSTUVWXYZ, 0123456789."
   ```
   → **비밀번호 정책이 실제로 적용됨을 확인.**

2. 확인 메일 실수신 테스트는 이번 세션에서 **생략**함(사용자 결정) — Confirm email 토글이 켜져 있고 대시보드에 반영된 것만 확인. 실제 메일 도착 여부는 아직 미검증.
   - 참고: 테스트 중 `@example.com` 도메인으로는 Supabase가 `email_address_invalid`로 가입 자체를 막음(가짜/테스트 도메인 차단 추정). 나중에 실제 수신 테스트할 때는 실제로 받아볼 수 있는 이메일 주소(예: gmail) 사용 필요.

## 3. 다음 Unit이 알아야 할 것

- Confirm email은 켜져 있지만 **아직 Supabase 기본 메일러**를 쓰는 중 (커스텀 SMTP 미연결)
- 비밀번호 최소 요구사항: 8자 이상 + 소문자/대문자/숫자 각 1개 이상 (프론트엔드 U04 가입 폼에서 이 조건을 안내/검증하면 좋음)
- U04(로그인 화면)에서 실제 가입 테스트할 때는 `@example.com` 같은 테스트 도메인 대신 실제 수신 가능한 이메일 주소를 사용할 것

## 4. 미해결/보류 이슈

- **커스텀 SMTP 미연결** — Resend/SendGrid/SES/Postmark 중 택1 필요, 계정 생성 및 API 키 발급은 사용자가 직접 해야 함(Claude가 대신 계정 생성/키 입력 불가). U12(출시 전 최종 점검)에서 처리 예정.
- **Leaked password protection(HaveIBeenPwned 연동) 비활성화 상태** — Supabase 대시보드에 "Only available on Pro plan and above"로 명시됨. 현재 Free 플랜이라 켤 수 없음. Pro 플랜으로 업그레이드 시 켜야 함.
- **CAPTCHA(hCaptcha/Turnstile) 미설정** — 외부 서비스 계정 필요(Cloudflare 또는 hCaptcha), 사이트키/시크릿키 발급 및 대시보드 입력은 사용자가 직접 해야 함. U04(로그인/가입 화면 제작) 시점에 실제 폼과 함께 연동하는 것으로 결정.
- 확인 메일 실제 수신 테스트 미완료(위 2번 참고)
