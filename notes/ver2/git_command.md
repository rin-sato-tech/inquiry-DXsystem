# WBS-0: 開発環境構築@ver2

## 1. `branch`とは何か

`branch` は、ざっくり言うと 作業の分岐先 です。

```text
main
  └─ Ver.1として完成済みの安定版

feature/ver2-enhancement
  └─ Ver.2開発用の作業場所
```

`main` は公開済みの安定版として残しておきます。Ver.2の開発は `main` を直接いじらず、`feature/ver2-enhancement` で進めます。イメージはこうです。

```text
A --- B --- C  main
              \
               D --- E --- F  feature/ver2-enhancement
```

この場合、C がVer.1完成時点です。そこから分岐して、D, E, F でVer.2の作業を進めます。

## 2. `tag`とは何か

`tag` は、特定のコミットに付ける 名前付きのしおり です。ブランチと違って、基本的には動きません。
今回なら、`v1.0.0 = Ver.1完成時点のコミット`という意味です。イメージはこうです。

```text
A --- B --- C  main
              ↑
            v1.0.0
```

v1.0.0 は「この時点が初期版完成です」という目印です。

## 3. `branch`と`tag`の違い

| 項目     | branch                     | tag                    |
| -------- | -------------------------- | ---------------------- |
| 役割     | 作業場所                   | 特定時点のしおり       |
| 動くか   | 新しいコミットをすると進む | 基本的に動かない       |
| 用途     | 開発を分ける               | リリース時点を保存する |
| 今回の例 | `feature/ver2-enhancement` | `v1.0.0`               |

重要なのはここです。

```text
branch は「これから作業する場所」
tag は「ここが完成版だったという目印」
```

## 4. 今回目指しているGitの状態

理想状態はこうです。

```text
main
└─ Ver.1完成版

v1.0.0
└─ Ver.1完成時点につけたタグ

feature/ver2-enhancement
└─ Ver.2開発用ブランチ
```

## 5. なぜこの状態にするのか

理由は、Ver.2開発で壊してもVer.1に戻れるようにするためです。
たとえばVer.2でDB構造を変えたり、画面を大きく改修したりすると、途中で不具合が出る可能性があります。そのときに `main` を直接いじっていると、公開済みの安定版まで壊れます。
でも、ブランチを分けていれば、

```text
main は安定版として残る
feature/ver2-enhancement で自由に改修できる
```

という状態になります。

さらに v1.0.0 タグがあると、

```bash
git checkout v1.0.0
```

で、Ver.1完成時点を確認できます。

## 6. 確認コマンド

現在のブランチを見るには、

```bash
git branch
```

たとえばこう出れば、Ver.2ブランチで作業中です。

```text
main
* feature/ver2-enhancement
```

`*` が今いるブランチです。

タグを見るには、

```bash
git tag
```

こう出ればOKです。

```text
v1.0.0
```

リモートも含めて確認するなら、

```bash
git branch -a
```

たとえばこうです。

```text
  main
* feature/ver2-enhancement
  remotes/origin/main
  remotes/origin/feature/ver2-enhancement
```

## 7. よくある誤解

### `tag`はブランチではない

v1.0.0 は作業場所ではありません。あくまで「この時点がVer.1完成」というラベルです。なので、通常は v1.0.0 上で作業しません。

### `branch`はタグではない

`feature/ver2-enhancement` は作業場所です。ここでは新しいコミットを積んでいきます。

```bash
git add .
git commit -m "Add Ver2 alert feature"
```

のようにすると、`feature/ver2-enhancement` が前に進みます。

## 8. 今後の流れ

Ver.2開発中は、基本的にこのブランチで作業します。

```bash
git checkout feature/ver2-enhancement
```

作業して、

```bash
git add .
git commit -m "Add Ver2 requirements"
git push
```

Ver.2が完成したら、最終的に `main` に取り込みます。

```bash
git checkout main
git merge feature/ver2-enhancement
git push
```

その後、Ver.2完成版にタグを付けます。

```bash
git tag -a v2.0.0 -m "Ver2 enhancement release"
git push origin v2.0.0
```

## 9. まとめ

今回のGit状態は、こう理解すればよいです。

```text
main
= Ver.1の安定版

v1.0.0
= Ver.1完成時点のしおり

feature/ver2-enhancement
= Ver.2を開発するための作業ブランチ
```

この形にしておくと、Ver.1の完成状態を守りながら、安心してVer.2のDB拡張・画面追加・FAQ候補管理などを進められます。
