# 画面設計

## 1. 画面構成

Streamlitアプリは以下の4タブ構成とする。

| タブ           | 目的                                     |
| -------------- | ---------------------------------------- |
| 問い合わせ一覧 | 全問い合わせの確認、検索、絞り込み       |
| 新規登録       | 問い合わせの新規登録                     |
| ステータス更新 | 担当者、ステータス、対応内容の更新       |
| 集計・CSV出力  | 件数集計、期限超過確認、Tableau用CSV出力 |

## 2. 問い合わせ一覧画面

### 目的

管理部が問い合わせ状況を一覧で確認する。

### 表示項目

| 項目         | 内容           |
| ------------ | -------------- |
| request_id   | 問い合わせID   |
| request_date | 受付日         |
| requester    | 依頼者         |
| department   | 部署           |
| channel      | 受付経路       |
| category     | カテゴリ       |
| subcategory  | 小分類         |
| priority     | 優先度         |
| due_date     | 希望期限       |
| assignee     | 担当者         |
| status       | ステータス     |
| overdue_flag | 期限超過       |
| detail       | 問い合わせ内容 |

### フィルタ項目

| フィルタ     | 内容                |
| ------------ | ------------------- |
| 部署         | department          |
| カテゴリ     | category            |
| 担当者       | assignee            |
| ステータス   | status              |
| 優先度       | priority            |
| 期限超過のみ | overdue_flag = True |

### KPI表示

画面上部に以下を表示する。

| KPI          | 内容                       |
| ------------ | -------------------------- |
| 全件数       | 登録されている問い合わせ数 |
| 未完了件数   | statusが完了以外の件数     |
| 期限超過件数 | 未完了かつ期限切れの件数   |
| 本日受付件数 | request_dateが本日の件数   |

## 3. 新規登録画面

### 目的

問い合わせをフォームから登録する。

### 入力項目

| 項目         | 必須 | 初期値                |
| ------------ | ---- | --------------------- |
| requester    | 必須 | なし                  |
| department   | 必須 | configから選択        |
| channel      | 必須 | フォーム              |
| category     | 必須 | configから選択        |
| subcategory  | 任意 | なし                  |
| detail       | 必須 | なし                  |
| missing_info | 任意 | なし                  |
| priority     | 必須 | 中                    |
| due_date     | 必須 | 今日から3営業日後程度 |
| assignee     | 任意 | 未設定                |
| status       | 必須 | 未対応                |

### 登録時の処理

- request_idを自動発行する
- request_dateを登録する
- request_timeを登録する
- completed_dateは空欄にする
- management_minutesは初期値0または空欄にする
- actual_response_minutesは初期値0または空欄にする

## 4. ステータス更新画面

### 目的

管理部が対応状況を更新する。

### 更新項目

| 項目                    | 内容                                     |
| ----------------------- | ---------------------------------------- |
| request_id              | 更新対象                                 |
| assignee                | 担当者                                   |
| status                  | 未対応、対応中、情報待ち、承認待ち、完了 |
| response_summary        | 対応内容                                 |
| completed_date          | 完了日                                   |
| management_minutes      | 管理作業時間                             |
| actual_response_minutes | 実対応時間                               |

### 完了時の処理

- statusを完了にした場合、completed_dateを入力する
- completed_dateが未入力の場合は警告を出す
- response_daysを集計処理で計算する

## 5. 集計・CSV出力画面

### 目的

問い合わせ状況を集計し、Tableau用CSVを出力する。

### 表示する集計

| 集計             | 内容                     |
| ---------------- | ------------------------ |
| カテゴリ別件数   | categoryごとの件数       |
| ステータス別件数 | statusごとの件数         |
| 担当者別件数     | assigneeごとの件数       |
| 部署別件数       | departmentごとの件数     |
| 受付経路別件数   | channelごとの件数        |
| 期限超過件数     | overdue_flagがTrueの件数 |
| 管理作業時間     | management_minutesの合計 |

### CSV出力

Tableau用に以下の追加列を含めてCSV出力する。

| 追加列                | 内容                       |
| --------------------- | -------------------------- |
| month                 | 受付月                     |
| overdue_flag          | 期限超過フラグ             |
| is_completed          | 完了済みフラグ             |
| is_open               | 未完了フラグ               |
| response_days         | 受付日から完了日までの日数 |
| management_hours      | 管理作業時間               |
| actual_response_hours | 実対応時間                 |
