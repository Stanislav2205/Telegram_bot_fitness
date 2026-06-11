# Metrics Spec

## Core KPI

- `newSubscribersFromCampaign`: новые подписчики канала за период кампании.
- `verifiedReferrals`: количество рефералов со статусом `verified`.
- `costPerVerifiedReferral`: стоимость призового фонда / `verifiedReferrals`.
- `retentionD1`, `retentionD7`: доля пользователей, оставшихся подписанными через 1 и 7 дней.

## Funnel

- `postViews`: охват анонс-поста.
- `botStarts`: количество `/start`.
- `subscriptionChecks`: нажатия `Проверить подписку`.
- `verifiedUsers`: пользователи, прошедшие `getChatMember` проверку.
- `activeReferrers`: пользователи, у кого >=1 подтвержденного реферала.

## SQL References

- `verifiedReferrals`: count from `referrals` where `status='verified'`.
- `ticketsByUser`: sum `tickets.amount` grouped by `user_id`.
- `drawAudit`: rows in `draw_results` + `audit_logs` for `draw.finished`.

## Weekly Review

- Сравнить конверсию `botStarts -> verifiedUsers`.
- Сравнить долю подозрительных/отклоненных рефералов.
- Оценить удержание новых подписчиков.
- Принять решение: менять приз, сроки или правила.
