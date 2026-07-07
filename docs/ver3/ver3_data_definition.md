# Ver.3 データ定義書

## 1. 目的

本ドキュメントは、社内問い合わせ管理システム Ver.3 で追加・変更するデータ構造を定義するものである。

Ver.2までは、問い合わせ本体である `inquiries` テーブルを中心に、FAQ候補、カテゴリ別追加情報、依頼者向け表示フラグなどを同一テーブル内に保持していた。
Ver.3では、簡易ログイン、FAQ公開、通知対象抽出、操作履歴、ステータス履歴、コメント履歴を扱うため、複数テーブル構成へ拡張する。

ただし、Ver.3では大規模なDB移行やPostgreSQL化は行わない。SQLiteを継続利用し、既存の `inquiries` テーブルを問い合わせ本体として残したまま、必要なテーブルを追加する。

---

## 2. Ver.2までのデータ構造

Ver.2時点では、主に以下のテーブルを利用している。

| テーブル    | 内容                                                                        |
| ----------- | --------------------------------------------------------------------------- |
| `inquiries` | 問い合わせ本体、FAQ候補、追加情報、依頼者表示フラグ、対応時間などを管理する |

Ver.2の `inquiries` テーブルには、以下のような情報が含まれている。

| 分類               | 主なカラム                                                                                                              |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| 問い合わせ基本情報 | `request_id`, `request_date`, `request_time`, `requester`, `department`, `channel`, `category`, `subcategory`, `detail` |
| 対応管理           | `priority`, `due_date`, `assignee`, `status`, `response_summary`, `completed_date`                                      |
| Ver.2追加情報      | `faq_candidate`, `faq_title`, `faq_answer`, `additional_info`, `requester_visible`, `last_status_changed_at`            |
| 工数情報           | `management_minutes`, `actual_response_minutes`                                                                         |
| システム管理情報   | `created_at`, `updated_at`                                                                                              |

Ver.3でも、`inquiries` は問い合わせ本体として継続利用する。

---

## 3. Ver.3で追加するテーブル

Ver.3では、以下のテーブルを追加する。

| テーブル            | 内容                                         |
| ------------------- | -------------------------------------------- |
| `users`             | 簡易ログイン用の利用者情報とロールを管理する |
| `faq_items`         | 依頼者向けに公開するFAQを管理する            |
| `inquiry_comments`  | 問い合わせごとのコメント・対応メモを管理する |
| `status_history`    | ステータス変更履歴を管理する                 |
| `operation_logs`    | 操作履歴を管理する                           |
| `notification_logs` | 通知対象・通知文生成履歴を管理する           |

Ver.3では、`roles` テーブルは作成しない。ロールは `users.role` に文字列として保持する。理由は、Ver.3では本格的な権限マスタ管理よりも、簡易ログインとロール別表示制御の実装を優先するためである。

---

## 4. テーブル一覧

|  No | テーブル            | 新規/既存 | 主キー            | 用途                     |
| --: | ------------------- | --------- | ----------------- | ------------------------ |
|   1 | `inquiries`         | 既存      | `request_id`      | 問い合わせ本体           |
|   2 | `users`             | 新規      | `user_id`         | 利用者・ロール管理       |
|   3 | `faq_items`         | 新規      | `faq_id`          | 公開FAQ管理              |
|   4 | `inquiry_comments`  | 新規      | `comment_id`      | コメント履歴             |
|   5 | `status_history`    | 新規      | `history_id`      | ステータス変更履歴       |
|   6 | `operation_logs`    | 新規      | `log_id`          | 操作履歴                 |
|   7 | `notification_logs` | 新規      | `notification_id` | 通知対象・通知文生成履歴 |

---

## 5. 既存テーブル定義

## 5.1 `inquiries`

### 5.1.1 目的

問い合わせ本体を管理する。
Ver.3でも、問い合わせの基本情報、現在の担当者、現在のステータス、対応概要、完了日などは `inquiries` に保持する。

### 5.1.2 主キー

| カラム       | 内容         |
| ------------ | ------------ |
| `request_id` | 問い合わせID |

### 5.1.3 カラム定義

| カラム                    | 型      | NOT NULL | デフォルト | 内容                     |
| ------------------------- | ------- | -------: | ---------- | ------------------------ |
| `request_id`              | TEXT    |      Yes | -          | 問い合わせID             |
| `request_date`            | TEXT    |      Yes | -          | 受付日                   |
| `request_time`            | TEXT    |       No | -          | 受付時刻                 |
| `requester`               | TEXT    |      Yes | -          | 依頼者名                 |
| `department`              | TEXT    |      Yes | -          | 依頼部署                 |
| `channel`                 | TEXT    |      Yes | -          | 受付経路                 |
| `category`                | TEXT    |      Yes | -          | 問い合わせカテゴリ       |
| `subcategory`             | TEXT    |       No | -          | サブカテゴリ             |
| `detail`                  | TEXT    |      Yes | -          | 問い合わせ内容           |
| `missing_info`            | TEXT    |       No | -          | 不足情報                 |
| `priority`                | TEXT    |      Yes | -          | 優先度                   |
| `due_date`                | TEXT    |      Yes | -          | 希望期限                 |
| `assignee`                | TEXT    |       No | -          | 担当者                   |
| `status`                  | TEXT    |      Yes | -          | 現在ステータス           |
| `response_summary`        | TEXT    |       No | -          | 対応概要                 |
| `record_issue`            | TEXT    |       No | -          | 記録上の問題             |
| `completed_date`          | TEXT    |       No | -          | 完了日                   |
| `faq_candidate`           | INTEGER |       No | 0          | FAQ候補フラグ            |
| `faq_title`               | TEXT    |       No | `''`       | FAQ候補タイトル          |
| `faq_answer`              | TEXT    |       No | `''`       | FAQ候補回答案            |
| `additional_info`         | TEXT    |       No | `''`       | カテゴリ別追加情報       |
| `requester_visible`       | INTEGER |       No | 1          | 依頼者向け表示対象フラグ |
| `last_status_changed_at`  | TEXT    |       No | `''`       | 最終ステータス変更日時   |
| `management_minutes`      | INTEGER |       No | 0          | 管理作業時間             |
| `actual_response_minutes` | INTEGER |       No | 0          | 実対応時間               |
| `created_at`              | TEXT    |      Yes | -          | 作成日時                 |
| `updated_at`              | TEXT    |      Yes | -          | 更新日時                 |

### 5.1.4 Ver.3での扱い

| 項目                                       | 方針                                                                   |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| 問い合わせ本体                             | 継続利用する                                                           |
| `faq_candidate`, `faq_title`, `faq_answer` | `faq_items` 作成時の移行元として利用する                               |
| `additional_info`                          | Ver.3でも継続利用する                                                  |
| `requester_visible`                        | 依頼者向け表示制御に継続利用する                                       |
| `assignee`                                 | 当面は担当者名の文字列として継続利用する                               |
| `status`                                   | 現在ステータスとして継続利用し、変更履歴は `status_history` に保存する |

---

## 6. 新規テーブル定義

## 6.1 `users`

### 6.1.1 目的

簡易ログイン用の利用者情報を管理する。Ver.3では、ユーザー選択式の簡易ログインを行い、`role` に応じて画面表示・操作範囲を切り替える。

### 6.1.2 主キー

| カラム    | 内容       |
| --------- | ---------- |
| `user_id` | ユーザーID |

### 6.1.3 カラム定義

| カラム       | 型      | NOT NULL | デフォルト | 内容               |
| ------------ | ------- | -------: | ---------- | ------------------ |
| `user_id`    | TEXT    |      Yes | -          | ユーザーID         |
| `user_name`  | TEXT    |      Yes | -          | 利用者名           |
| `department` | TEXT    |       No | `''`       | 所属部署           |
| `email`      | TEXT    |       No | `''`       | メールアドレス     |
| `role`       | TEXT    |      Yes | -          | ロール             |
| `is_active`  | INTEGER |       No | 1          | 有効ユーザーフラグ |
| `created_at` | TEXT    |      Yes | -          | 作成日時           |
| `updated_at` | TEXT    |      Yes | -          | 更新日時           |

### 6.1.4 `role` の値

| 値          | 意味         |
| ----------- | ------------ |
| `requester` | 依頼者       |
| `staff`     | 管理部担当者 |
| `admin`     | 管理者       |
| `viewer`    | 閲覧者       |

### 6.1.5 制約・補足

| 項目         | 内容                                                        |
| ------------ | ----------------------------------------------------------- |
| ロール管理   | Ver.3では `roles` テーブルを作らず、`users.role` で管理する |
| パスワード   | Ver.3では保持しない                                         |
| 本格認証     | Ver.3の対象外とする                                         |
| デモユーザー | 初期データとして各ロールのサンプルユーザーを用意する        |

---

## 6.2 `faq_items`

### 6.2.1 目的

依頼者向けに公開するFAQを管理する。Ver.2のFAQ候補を元に、Ver.3では公開FAQとして独立管理する。

### 6.2.2 主キー

| カラム   | 内容   |
| -------- | ------ |
| `faq_id` | FAQ ID |

### 6.2.3 カラム定義

| カラム              | 型      | NOT NULL | デフォルト | 内容                   |
| ------------------- | ------- | -------: | ---------- | ---------------------- |
| `faq_id`            | TEXT    |      Yes | -          | FAQ ID                 |
| `source_request_id` | TEXT    |       No | `''`       | 元になった問い合わせID |
| `category`          | TEXT    |      Yes | -          | FAQカテゴリ            |
| `title`             | TEXT    |      Yes | -          | FAQタイトル            |
| `answer`            | TEXT    |      Yes | -          | FAQ回答                |
| `is_public`         | INTEGER |       No | 0          | 公開フラグ             |
| `view_count`        | INTEGER |       No | 0          | 閲覧回数               |
| `helpful_count`     | INTEGER |       No | 0          | 役立ち件数             |
| `created_by`        | TEXT    |       No | `''`       | 作成者ユーザーID       |
| `updated_by`        | TEXT    |       No | `''`       | 更新者ユーザーID       |
| `created_at`        | TEXT    |      Yes | -          | 作成日時               |
| `updated_at`        | TEXT    |      Yes | -          | 更新日時               |

### 6.2.4 外部キー方針

| カラム              | 参照先                 | 方針                         |
| ------------------- | ---------------------- | ---------------------------- |
| `source_request_id` | `inquiries.request_id` | 元問い合わせとの紐づけに使う |
| `created_by`        | `users.user_id`        | 作成者の記録に使う           |
| `updated_by`        | `users.user_id`        | 更新者の記録に使う           |

SQLiteでは外部キー制約を設定してもよいが、Ver.3では実装容易性を優先し、まずは参照関係として扱う。

### 6.2.5 Ver.2からの移行

`inquiries` の以下の条件を満たす行をFAQ候補として扱う。

| 条件                    | 内容                  |
| ----------------------- | --------------------- |
| `faq_candidate = 1`     | FAQ候補として登録済み |
| `faq_title` が空でない  | FAQタイトルが入力済み |
| `faq_answer` が空でない | FAQ回答案が入力済み   |

移行時は、以下の対応で `faq_items` に登録する。

| `inquiries`  | `faq_items`         |
| ------------ | ------------------- |
| `request_id` | `source_request_id` |
| `category`   | `category`          |
| `faq_title`  | `title`             |
| `faq_answer` | `answer`            |
| -            | `is_public = 0`     |
| -            | `view_count = 0`    |
| -            | `helpful_count = 0` |

---

## 6.3 `inquiry_comments`

### 6.3.1 目的

問い合わせごとのコメント・対応メモを管理する。Ver.2では `response_summary` に最新の対応概要を記録していたが、Ver.3では途中経過や確認事項を時系列で残せるようにする。

### 6.3.2 主キー

| カラム       | 内容       |
| ------------ | ---------- |
| `comment_id` | コメントID |

### 6.3.3 カラム定義

| カラム         | 型   | NOT NULL | デフォルト | 内容             |
| -------------- | ---- | -------: | ---------- | ---------------- |
| `comment_id`   | TEXT |      Yes | -          | コメントID       |
| `request_id`   | TEXT |      Yes | -          | 問い合わせID     |
| `comment_body` | TEXT |      Yes | -          | コメント本文     |
| `visibility`   | TEXT |       No | `internal` | 表示区分         |
| `created_by`   | TEXT |       No | `''`       | 投稿者ユーザーID |
| `created_at`   | TEXT |      Yes | -          | 投稿日時         |

### 6.3.4 `visibility` の値

| 値          | 意味               |
| ----------- | ------------------ |
| `internal`  | 管理部内部向け     |
| `requester` | 依頼者にも表示可能 |

### 6.3.5 表示方針

| ロール      | 表示範囲                                    |
| ----------- | ------------------------------------------- |
| `requester` | `visibility = requester` のコメントのみ表示 |
| `staff`     | 全コメントを表示                            |
| `admin`     | 全コメントを表示                            |
| `viewer`    | コメントは表示しない                        |

---

## 6.4 `status_history`

### 6.4.1 目的

問い合わせのステータス変更履歴を管理する。`inquiries.status` は現在ステータスとして残し、変更履歴は `status_history` に保存する。

### 6.4.2 主キー

| カラム       | 内容   |
| ------------ | ------ |
| `history_id` | 履歴ID |

### 6.4.3 カラム定義

| カラム       | 型   | NOT NULL | デフォルト | 内容             |
| ------------ | ---- | -------: | ---------- | ---------------- |
| `history_id` | TEXT |      Yes | -          | ステータス履歴ID |
| `request_id` | TEXT |      Yes | -          | 問い合わせID     |
| `old_status` | TEXT |       No | `''`       | 変更前ステータス |
| `new_status` | TEXT |      Yes | -          | 変更後ステータス |
| `changed_by` | TEXT |       No | `''`       | 変更者ユーザーID |
| `changed_at` | TEXT |      Yes | -          | 変更日時         |

### 6.4.4 登録タイミング

| タイミング           | 登録内容                                     |
| -------------------- | -------------------------------------------- |
| 問い合わせ新規作成時 | 初期ステータスを `new_status` として保存する |
| ステータス変更時     | 変更前後のステータスを保存する               |
| 完了処理時           | 完了ステータスへの変更を保存する             |

### 6.4.5 表示方針

| ロール      | 表示可否             |
| ----------- | -------------------- |
| `requester` | 原則非表示           |
| `staff`     | 担当案件について表示 |
| `admin`     | 全件表示             |
| `viewer`    | 非表示               |

---

## 6.5 `operation_logs`

### 6.5.1 目的

主要な操作履歴を管理する。
誰が、いつ、どのデータに対して、どのような操作を行ったかを追跡できるようにする。

### 6.5.2 主キー

| カラム   | 内容       |
| -------- | ---------- |
| `log_id` | 操作ログID |

### 6.5.3 カラム定義

| カラム         | 型   | NOT NULL | デフォルト | 内容           |
| -------------- | ---- | -------: | ---------- | -------------- |
| `log_id`       | TEXT |      Yes | -          | 操作ログID     |
| `user_id`      | TEXT |       No | `''`       | 操作ユーザーID |
| `action`       | TEXT |      Yes | -          | 操作種別       |
| `target_table` | TEXT |      Yes | -          | 対象テーブル   |
| `target_id`    | TEXT |      Yes | -          | 対象ID         |
| `detail`       | TEXT |       No | `''`       | 操作内容       |
| `created_at`   | TEXT |      Yes | -          | 操作日時       |

### 6.5.4 `action` の主な値

| 値                      | 意味           |
| ----------------------- | -------------- |
| `create_inquiry`        | 問い合わせ作成 |
| `update_inquiry`        | 問い合わせ更新 |
| `change_status`         | ステータス変更 |
| `change_assignee`       | 担当者変更     |
| `create_faq`            | FAQ作成        |
| `update_faq`            | FAQ更新        |
| `publish_faq`           | FAQ公開        |
| `unpublish_faq`         | FAQ非公開      |
| `create_comment`        | コメント追加   |
| `generate_notification` | 通知文生成     |

### 6.5.5 表示方針

| ロール      | 表示可否   |
| ----------- | ---------- |
| `requester` | 非表示     |
| `staff`     | 原則非表示 |
| `admin`     | 表示       |
| `viewer`    | 非表示     |

---

## 6.6 `notification_logs`

### 6.6.1 目的

通知対象として抽出された問い合わせと、生成した通知文を管理する。
Ver.3では、外部メール・Slackへの実送信は行わず、通知対象抽出と通知文生成までを対象とする。

### 6.6.2 主キー

| カラム            | 内容       |
| ----------------- | ---------- |
| `notification_id` | 通知ログID |

### 6.6.3 カラム定義

| カラム              | 型   | NOT NULL | デフォルト | 内容               |
| ------------------- | ---- | -------: | ---------- | ------------------ |
| `notification_id`   | TEXT |      Yes | -          | 通知ログID         |
| `request_id`        | TEXT |      Yes | -          | 問い合わせID       |
| `notification_type` | TEXT |      Yes | -          | 通知種別           |
| `recipient_user_id` | TEXT |       No | `''`       | 通知対象ユーザーID |
| `message`           | TEXT |      Yes | -          | 通知文面           |
| `status`            | TEXT |       No | `created`  | 通知状態           |
| `created_at`        | TEXT |      Yes | -          | 作成日時           |

### 6.6.4 `notification_type` の値

| 値                 | 意味           |
| ------------------ | -------------- |
| `before_due`       | 期限前         |
| `overdue`          | 期限超過       |
| `unassigned`       | 担当者未設定   |
| `waiting_too_long` | 情報待ち長期化 |
| `status_changed`   | ステータス変更 |
| `completed`        | 完了通知       |

### 6.6.5 `status` の値

| 値         | 意味                             |
| ---------- | -------------------------------- |
| `created`  | 通知文生成済み                   |
| `reviewed` | 管理者確認済み                   |
| `skipped`  | 通知対象から除外                 |
| `sent`     | 将来的な外部送信済みを想定した値 |

Ver.3では実送信を行わないため、基本的には `created` または `reviewed` を使用する。

---

## 7. リレーション

Ver.3の主なリレーションは以下である。

| 元テーブル          | カラム              | 参照先                 | 用途                         |
| ------------------- | ------------------- | ---------------------- | ---------------------------- |
| `faq_items`         | `source_request_id` | `inquiries.request_id` | FAQの元問い合わせ            |
| `faq_items`         | `created_by`        | `users.user_id`        | FAQ作成者                    |
| `faq_items`         | `updated_by`        | `users.user_id`        | FAQ更新者                    |
| `inquiry_comments`  | `request_id`        | `inquiries.request_id` | コメント対象問い合わせ       |
| `inquiry_comments`  | `created_by`        | `users.user_id`        | コメント投稿者               |
| `status_history`    | `request_id`        | `inquiries.request_id` | ステータス変更対象問い合わせ |
| `status_history`    | `changed_by`        | `users.user_id`        | ステータス変更者             |
| `operation_logs`    | `user_id`           | `users.user_id`        | 操作ユーザー                 |
| `notification_logs` | `request_id`        | `inquiries.request_id` | 通知対象問い合わせ           |
| `notification_logs` | `recipient_user_id` | `users.user_id`        | 通知対象ユーザー             |

SQLiteでは外部キー制約を設定することもできるが、Ver.3では実装容易性を優先し、まずはアプリケーション側で整合性を管理する。

---

## 8. インデックス方針

Ver.3では、検索・絞り込みで使用するカラムにインデックスを追加する。

### 8.1 既存インデックス

既存の `inquiries` では、以下のインデックスを継続利用する。

| インデックス対象 | 用途                     |
| ---------------- | ------------------------ |
| `request_date`   | 受付日での並び替え・集計 |
| `due_date`       | 期限超過・期限前判定     |
| `status`         | ステータス別絞り込み     |
| `category`       | カテゴリ別集計           |
| `assignee`       | 担当者別絞り込み         |

### 8.2 Ver.3追加インデックス案

| テーブル            | カラム              | 用途                           |
| ------------------- | ------------------- | ------------------------------ |
| `users`             | `role`              | ロール別ユーザー取得           |
| `users`             | `is_active`         | 有効ユーザー取得               |
| `faq_items`         | `category`          | FAQカテゴリ絞り込み            |
| `faq_items`         | `is_public`         | 公開FAQ取得                    |
| `faq_items`         | `source_request_id` | 元問い合わせとの紐づけ         |
| `inquiry_comments`  | `request_id`        | 問い合わせ別コメント取得       |
| `status_history`    | `request_id`        | 問い合わせ別ステータス履歴取得 |
| `operation_logs`    | `target_id`         | 対象ID別操作履歴取得           |
| `operation_logs`    | `created_at`        | 操作日時順表示                 |
| `notification_logs` | `request_id`        | 問い合わせ別通知履歴取得       |
| `notification_logs` | `notification_type` | 通知種別別集計                 |
| `notification_logs` | `created_at`        | 通知作成日別集計               |

---

## 9. ID採番方針

Ver.3で追加するIDは、可読性を重視した文字列IDとする。

| 対象             | 形式例         |
| ---------------- | -------------- |
| ユーザーID       | `U001`, `U002` |
| FAQ ID           | `FAQ-0001`     |
| コメントID       | `COM-0001`     |
| ステータス履歴ID | `STH-0001`     |
| 操作ログID       | `LOG-0001`     |
| 通知ログID       | `NTF-0001`     |

開発初期は、既存の件数から連番を生成する簡易方式でよい。将来的に同時登録や本格運用を想定する場合は、UUIDまたは日時ベースIDへの変更を検討する。

---

## 10. 初期データ方針

Ver.3では、簡易ログインとロール別表示を確認するため、`users` に初期データを登録する。

| user_id | user_name | department | role        | 用途             |
| ------- | --------- | ---------- | ----------- | ---------------- |
| `U001`  | 山田 太郎 | 営業部     | `requester` | 依頼者デモ       |
| `U002`  | 佐藤 花子 | 管理部     | `staff`     | 管理部担当者デモ |
| `U003`  | 鈴木 一郎 | 管理部     | `admin`     | 管理者デモ       |
| `U004`  | 高橋 美咲 | 経営企画部 | `viewer`    | 閲覧者デモ       |

氏名は架空データとして扱う。実在人物の個人情報は使用しない。

---

## 11. Ver.2からVer.3への移行方針

### 11.1 基本方針

Ver.3では、既存の `inquiries` テーブルを壊さずに、追加テーブルを作成する。

| 項目                 | 方針                                          |
| -------------------- | --------------------------------------------- |
| 既存問い合わせ       | 継続利用する                                  |
| 既存FAQ候補          | `faq_items` への移行元として扱う              |
| 既存追加情報         | `additional_info` として継続利用する          |
| 既存依頼者表示フラグ | `requester_visible` として継続利用する        |
| 既存ステータス       | `inquiries.status` を現在値として継続利用する |

### 11.2 FAQ移行

`inquiries` のFAQ候補を `faq_items` に移行する。

移行対象条件は以下とする。

```text
faq_candidate = 1
faq_title != ''
faq_answer != ''
```

移行後のFAQは、初期状態では非公開とする。

| 項目            | 初期値 |
| --------------- | ------ |
| `is_public`     | 0      |
| `view_count`    | 0      |
| `helpful_count` | 0      |

管理者が内容を確認したうえで、公開・非公開を切り替える。

### 11.3 ステータス履歴の初期化

既存問い合わせについては、移行時点の `status` を現在ステータスとして扱う。過去の変更履歴は存在しないため、移行時に初期履歴を作るかどうかは任意とする。
Ver.3では、原則としてVer.3以降に発生したステータス変更から `status_history` に保存する。

---

## 12. Ver.3では見送るデータ設計

以下はVer.3では見送る。

| 見送る設計                 | 理由                                                           |
| -------------------------- | -------------------------------------------------------------- |
| `roles` テーブル           | ロール数が少なく、`users.role` で十分管理できるため            |
| `user_roles` テーブル      | 1ユーザー1ロールの簡易設計で十分なため                         |
| 添付ファイルテーブル       | ファイル保存先・容量・権限管理が別途必要なため                 |
| FAQ閲覧ログの詳細テーブル  | Ver.3では `view_count`、`helpful_count` のカウンタで十分なため |
| 承認ワークフローテーブル   | Ver.3の主目的から外れるため                                    |
| 通知送信キュー             | 外部送信をVer.3対象外とするため                                |
| PostgreSQL前提の高度な制約 | SQLiteでの小規模業務アプリを想定するため                       |

---

## 13. データ設計上の注意点

### 13.1 `inquiries.assignee` の扱い

Ver.3では `users` テーブルを追加するが、`inquiries.assignee` は当面文字列のまま継続する。理由は以下である。

| 理由         | 内容                                         |
| ------------ | -------------------------------------------- |
| 既存機能維持 | Ver.2の担当者別集計・絞り込みを壊さないため  |
| 移行容易性   | 既存データを大きく変えずにVer.3へ進めるため  |
| 実装量抑制   | 担当者ID化は後続バージョンでも対応可能なため |

将来的には、`assignee_user_id` を追加し、`users.user_id` と紐づけることを検討する。

### 13.2 `additional_info` の扱い

Ver.3では `additional_info` を継続利用する。ただし、カテゴリ別入力内容を詳細分析する場合、現在のTEXT形式では扱いにくい。
Ver.3では実装負荷を抑えるため、`additional_info` の正規化は見送る。後続バージョンでは、以下のいずれかを検討する。

| 案           | 内容                                                  |
| ------------ | ----------------------------------------------------- |
| JSON形式化   | `additional_info_json` として構造化保存する           |
| 子テーブル化 | `inquiry_additional_fields` にkey-value形式で保存する |

### 13.3 FAQ公開時の情報管理

FAQを公開する際は、元問い合わせの個人情報や社内固有情報をそのまま公開しない。FAQタイトルと回答内容は、管理者が確認・編集したうえで公開する。

---

## 14. 作成予定SQL概要

実装時には、`schema.sql` に以下の `CREATE TABLE IF NOT EXISTS` を追加する。

```sql
CREATE TABLE IF NOT EXISTS users (...);

CREATE TABLE IF NOT EXISTS faq_items (...);

CREATE TABLE IF NOT EXISTS inquiry_comments (...);

CREATE TABLE IF NOT EXISTS status_history (...);

CREATE TABLE IF NOT EXISTS operation_logs (...);

CREATE TABLE IF NOT EXISTS notification_logs (...);
```

具体的なSQLはWBS2で実装する。本ドキュメントでは、テーブルの目的、カラム、データ方針を定義する。

---

## 15. 完了条件

Ver.3のデータ設計は、以下を満たした時点で完了とする。

| 項目             | 完了条件                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| 既存テーブル整理 | `inquiries` の継続利用方針が明確になっている                                                                       |
| 追加テーブル     | `users`, `faq_items`, `inquiry_comments`, `status_history`, `operation_logs`, `notification_logs` が定義されている |
| ロール管理       | `users.role` による簡易ロール管理方針が決まっている                                                                |
| FAQ移行          | Ver.2のFAQ候補から `faq_items` への移行方針が決まっている                                                          |
| 履歴管理         | 操作履歴、ステータス履歴、コメント履歴の保存先が決まっている                                                       |
| 通知管理         | 通知対象と通知文を `notification_logs` に保存する方針が決まっている                                                |
| 対象外           | rolesテーブル、添付ファイル、詳細FAQ閲覧ログなどの見送り理由が明記されている                                       |

---

## 16. 結論

Ver.3では、既存の `inquiries` テーブルを問い合わせ本体として継続利用しつつ、利用者、FAQ、コメント、ステータス履歴、操作履歴、通知ログを別テーブルとして追加する。
これにより、Ver.2まで `inquiries` に集約していた情報を、用途ごとに分離できる。特に、FAQ公開、ロール別表示、通知対象抽出、履歴管理を実装するうえで、複数テーブル化は必要である。

一方で、Ver.3では実装範囲を広げすぎないため、`roles` テーブル、添付ファイル管理、FAQ閲覧詳細ログ、PostgreSQL移行は見送る。
この設計により、Ver.3では既存機能を維持しながら、問い合わせ管理アプリをより実運用に近い業務システムへ発展させる。
