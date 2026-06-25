# データ定義書

## 1. テーブル名

SQLiteのメインテーブル名は `inquiries` とする。

## 2. カラム定義

| カラム名                | 型      | 必須 | 内容                                   |
| ----------------------- | ------- | ---- | -------------------------------------- |
| request_id              | TEXT    | 必須 | 問い合わせID。REQ-YYYYMMDD-連番        |
| request_date            | TEXT    | 必須 | 受付日。YYYY-MM-DD                     |
| request_time            | TEXT    | 任意 | 受付時刻。HH:MM                        |
| requester               | TEXT    | 必須 | 依頼者名                               |
| department              | TEXT    | 必須 | 依頼者の所属部署                       |
| channel                 | TEXT    | 必須 | 受付経路                               |
| category                | TEXT    | 必須 | 問い合わせ大分類                       |
| subcategory             | TEXT    | 任意 | 問い合わせ小分類                       |
| detail                  | TEXT    | 必須 | 問い合わせ内容                         |
| missing_info            | TEXT    | 任意 | 初回問い合わせ時に不足していた情報     |
| priority                | TEXT    | 必須 | 優先度                                 |
| due_date                | TEXT    | 必須 | 希望期限。YYYY-MM-DD                   |
| assignee                | TEXT    | 任意 | 管理部担当者                           |
| status                  | TEXT    | 必須 | 対応状況                               |
| response_summary        | TEXT    | 任意 | 管理部の回答・対応内容                 |
| record_issue            | TEXT    | 任意 | DX化前の記録・管理上の問題             |
| completed_date          | TEXT    | 任意 | 完了日。YYYY-MM-DD                     |
| management_minutes      | INTEGER | 任意 | 転記・確認・進捗管理などの管理作業時間 |
| actual_response_minutes | INTEGER | 任意 | PC確認、権限付与などの実対応時間       |
| created_at              | TEXT    | 必須 | レコード作成日時                       |
| updated_at              | TEXT    | 必須 | レコード更新日時                       |

## 3. 派生項目

以下はDBに保存せず、表示・出力時に計算してもよい。

| 項目                  | 内容                                                   |
| --------------------- | ------------------------------------------------------ |
| overdue_flag          | statusが完了以外、かつdue_dateが今日より前の場合にTrue |
| response_days         | completed_date - request_date                          |
| month                 | request_dateの年月                                     |
| is_completed          | statusが完了ならTrue                                   |
| is_open               | statusが完了以外ならTrue                               |
| management_hours      | management_minutes / 60                                |
| actual_response_hours | actual_response_minutes / 60                           |

## 4. 値の定義

### department

- 営業部
- 業務部
- 施工管理部
- 倉庫・物流部
- 管理部
- 経営層

### channel

- フォーム
- メール
- 電話
- 口頭
- チャット
- Excel

DX化後の新規登録は原則として「フォーム」を使用する。

### category

- PC・システム
- アカウント・権限
- 経費・請求
- 勤怠・労務
- 備品・設備
- 契約・書類
- 車両・配送
- その他

### priority

- 高
- 中
- 低

### status

- 未対応
- 対応中
- 情報待ち
- 承認待ち
- 完了

## 5. ステータスの意味

| ステータス | 意味                                           |
| ---------- | ---------------------------------------------- |
| 未対応     | 受付済みだが、管理部がまだ対応を開始していない |
| 対応中     | 管理部が対応を進めている                       |
| 情報待ち   | 依頼者からの追加情報を待っている               |
| 承認待ち   | 上長や関係者の承認を待っている                 |
| 完了       | 対応が完了している                             |

## 6. 期限超過判定

期限超過は以下の条件で判定する。

```text
status != "完了"
and
due_date < 今日
```

## 7. request_id採番ルール

問い合わせIDは以下の形式とする。

`REQ-YYYYMMDD-001`

同日に複数登録される場合は、末尾の連番を増やす。

例：

REQ-20260625-001
REQ-20260625-002
REQ-20260625-003
