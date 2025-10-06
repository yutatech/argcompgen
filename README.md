# argcompgen

## Abstract
`argcompgen`は、pythonのargparseで実装されたCLIを解析し、zshとbash向けの補完スクリプトを生成します。
argcompleteが補完実行時にargcompleteに依存しているのに対して、`argcompgen`は一切の依存がありません。

## Installation
```
pip install git+https://github.com/yutatech/argcompgen.git
```

## Usage
`argcompgen`を使用するには、以下のコマンドを実行します。

```
argcompgen <script path> <bash | zsh>
```

ex:
```
argcompgen script.py zsh
```

## Temporary Usage of Completion Script
### zsh
`export fpath=( /path/to/_comp_script "${fpath[@]}" ) && compinit`

### bash
`source comp_script.bash`

## License
このプロジェクトはMITライセンスの下で提供されています。詳細は`LICENSE`ファイルを参照してください。