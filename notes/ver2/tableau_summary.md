# WBS7 学習ログ：既存集計・Tableau出力の更新

## 1. 今回やったこと

WBS3〜WBS6では、以下の機能を追加してきた。WBS7では、Ver.2追加機能を数値として確認できるようにし、Tableau側でも可視化できるようにした。

| WBS  | 追加機能               |
| ---- | ---------------------- |
| WBS3 | 要対応アラート         |
| WBS4 | FAQ候補管理            |
| WBS5 | カテゴリ別入力フォーム |
| WBS6 | 依頼者向け確認画面     |

Ver.1集計は「問い合わせの状態」を見るもの、Ver.2集計は「改善機能の活用状況」を見るものと整理できる。

## 2. 追加情報入力率の考え方

WBS5で追加した `additional_info` は、カテゴリ別入力フォームの入力結果を保存する列である。WBS7では、`additional_info` が空でない件数を数え、全問い合わせに対する割合を計算した。

```text
追加情報入力率 = 追加情報あり件数 / 全問い合わせ件数 × 100
```

この入力率を見ることで、カテゴリ別入力フォームがどれくらい利用されているかを確認できる。たとえば、入力率が低い場合は、以下のような原因が考えられる。

- 追加項目が分かりにくい
- 入力項目が多すぎる
- 依頼者が入力の必要性を理解していない
- カテゴリ別項目が実態に合っていない

つまり、追加情報入力率は、フォーム改善のための指標になる。

## 3. `faq_candidate_by_category()` の役割

`faq_candidate_by_category()` は、FAQ候補をカテゴリ別に集計する関数である。出力イメージは以下である。

| カテゴリ         | FAQ候補件数 |
| ---------------- | ----------: |
| PC・システム     |           5 |
| アカウント・権限 |           3 |
| 勤怠・労務       |           2 |

FAQ候補が多いカテゴリは、よくある問い合わせが多い領域と考えられる。そのため、FAQ整備の優先順位を考える材料になる。
たとえば、PC・システムやアカウント・権限にFAQ候補が多ければ、そのカテゴリのFAQを先に整備することで、問い合わせ削減効果が出やすい可能性がある。

## 4. CSV出力確認の方法

Tableau用CSVを出力するには、以下を実行する。

```bash
python -m src.export_tableau_csv
```

出力後、CSVの列を確認する。

```bash
python - << 'EOF'
import pandas as pd
from pathlib import Path

path = Path("data/tableau_output.csv")
df = pd.read_csv(path)

print("行数:", len(df))
print("列数:", len(df.columns))
print()
print(df.columns.tolist())
print()
print(df[
    [
        "request_id",
        "category",
        "additional_info",
        "has_additional_info_int",
        "faq_candidate_int",
        "requester_visible_int",
        "has_alert",
        "alert_type",
    ]
].head())
EOF
```

この確認により、Ver.2列がCSVに含まれているかを確認できる。

## 5. WBS7の動作確認

WBS7では、以下を確認する。

### 構文確認

```bash
python -m py_compile src/summary.py src/tableau_export.py app.py
```

### Ver.2集計確認

```bash
python -m src.check_ver2_summary
```

確認用スクリプトを作成していない場合は、直接Pythonコードで確認してもよい。

### Tableau CSV出力確認

```bash
python -m src.export_tableau_csv
```

## 6. 今後の実装とのつながり

WBS7で追加した集計・Tableau出力更新は、今後以下に展開できる。

| 今後の作業                | つながり                                          |
| ------------------------- | ------------------------------------------------- |
| Tableauダッシュボード更新 | Ver.2列を使って新しい可視化を作れる               |
| README更新                | Ver.2の改善効果を数値で説明できる                 |
| スクリーンショット作成    | 集計画面やTableau画面をポートフォリオに載せられる |
| WBS8テスト                | Ver.2追加集計とCSV出力の整合性を確認する          |
| WBS9ドキュメント更新      | Ver.2機能の説明に集計指標を入れられる             |
| WBS10ポートフォリオ反映   | Ver.2の成果として見せやすくなる                   |

WBS7では、Ver.2の各機能を単体で終わらせず、集計・可視化につなげた。

これにより、問い合わせ管理アプリは「登録・管理するツール」から、「改善状況を確認し、次の施策につなげるツール」へ発展した。
