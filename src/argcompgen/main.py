#!/usr/bin/env python3

import argparse
import os
import sys
import runpy
from textwrap import indent

captured_parser = None


def load_parser_safely(path: str) -> argparse.ArgumentParser:
    global captured_parser
    original_parse_args = argparse.ArgumentParser.parse_args

    def fake_parse_args(self, *args, **kwargs):
        """parse_args() が呼ばれた瞬間に捕捉して停止する"""
        global captured_parser
        captured_parser = self
        raise StopIteration("Parser captured before parsing args")

    # 一時的に差し替える
    argparse.ArgumentParser.parse_args = fake_parse_args

    try:
        # __main__ をシミュレートしてスクリプトを安全に実行
        runpy.run_path(path, run_name="__main__")
    except StopIteration:
        # 想定通り、parse_args直前で停止
        pass
    except Exception as e:
        print(f"❌ Error loading script: {e}")
        sys.exit(1)
    finally:
        # 元に戻す
        argparse.ArgumentParser.parse_args = original_parse_args

    if not captured_parser:
        print("❌ parser not found")

    return captured_parser


def generate_bash_completion(parser, prog_name: str, func_name=None, level=0):
    func_name = func_name or f"_{prog_name.replace('-', '_')}"
    indent = "    " * level
    script = []

    script.append(f"{func_name}() {{")
    script.append(f"{indent}local cur prev words cword")
    script.append(f"{indent}cur=${{COMP_WORDS[COMP_CWORD]}}")
    script.append(f"{indent}prev=${{COMP_WORDS[COMP_CWORD-1]}}")
    script.append(f"{indent}COMPREPLY=()")

    # オプションとそのタイプを収集
    options_store = []  # store
    options_flag = []  # store_true / store_false
    for a in parser._actions:
        if a.option_strings:
            if a.nargs in [0, None] and a.const in [
                True,
                False,
            ]:  # store_true / store_false
                options_flag.extend(a.option_strings)
            else:  # store または引数付き
                options_store.extend(a.option_strings)

    # 排他グループの解析
    mutex_groups = []
    for group in parser._mutually_exclusive_groups:
        group_opts = [o for a in group._group_actions for o in (a.option_strings or [])]
        if group_opts:
            mutex_groups.append(group_opts)

    # サブコマンドの処理
    subparsers_action = next(
        (a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None
    )
    if subparsers_action:
        subcommands = list(subparsers_action.choices.keys())
        script.append(f"{indent}local subcmds='{ ' '.join(subcommands) }'")

        script.append(f"{indent}if [ $COMP_CWORD -eq {level + 1} ]; then")
        # ここで store_true/false のみ表示、store は入力済みなら除外
        script.append(
            f"{indent}    COMPREPLY=( $(compgen -W \"$subcmds {' '.join(options_flag)}\" -- \"$cur\") )"
        )
        script.append(f"{indent}    return 0")
        script.append(f"{indent}fi")

        # サブコマンドごとの再帰
        script.append(f"{indent}case ${{COMP_WORDS[1]}} in")
        sub_command_func = []
        for subcmd, subparser in subparsers_action.choices.items():
            sub_func = f"{func_name}_{subcmd}"
            script.append(f"{indent}{subcmd})")
            script.append(f"{indent}{sub_func}")
            sub_command_func.append(
                generate_bash_completion(
                    subparser, prog_name, func_name=sub_func, level=level + 1
                )
            )
            script.append(f"{indent};;")
        script.append(f"{indent}esac")
        script.append(f"{indent}return 0")
    else:
        # store_true / store_false は未入力なら候補に出す
        script.append(f"{indent}local opts_flag=\"{' '.join(options_flag)}\"")
        script.append(f'{indent}for w in "${{COMP_WORDS[@]}}"; do')
        script.append(f"{indent}    opts_flag=(${{opts_flag[@]/$w/}})")
        script.append(f"{indent}done")

        # store オプションは候補に常に出す（1回だけ補完可能、入力済みを除外したい場合はここでチェック）
        script.append(f"{indent}local opts_store=\"{' '.join(options_store)}\"")

        # すべてのオプション候補をまとめる
        script.append(f"{indent}local opts_all=(${{opts_flag[@]}} $opts_store)")
        script.append(f'{indent}local opts_all_str="${{opts_all[*]}}"')
        script.append(
            f'{indent}COMPREPLY=( $(compgen -W "${{opts_all_str}}" -- "$cur") )'
        )
        script.append(f"{indent}return 0")

    script.append("}")
    if level == 0:
        script.append(f"complete -F {func_name} {prog_name}")

    if subparsers_action:
        script = sub_command_func + script

    return "\n".join(script)


def generate_zsh_completion(parser: argparse.ArgumentParser, prog_name=None, level=0):
    """argparse parser から zsh 補完スクリプトを再帰生成する"""
    if prog_name is None:
        prog_name = parser.prog

    lines = []

    lines.append(f"\n_{prog_name}() {{")

    # _arguments の構築
    args_lines = []
    state_cases = []

    # 排他グループを一時的にマーク
    exclusive_opts = set()
    for group in parser._mutually_exclusive_groups:
        group_opts = []
        for a in group._group_actions:
            if a.option_strings:
                group_opts.extend(a.option_strings)
        if group_opts:
            excl_str = f"({' '.join(group_opts)})"
            for a in group._group_actions:
                if a.option_strings:
                    if len(a.option_strings) == 1:
                        opts = a.option_strings[0]
                    else:
                        opts = "{" + ",".join(a.option_strings) + "}"
                    args_lines.append(f"'{excl_str}'{opts}'[{a.help or ''}]'")
                    exclusive_opts.update(a.option_strings)

    positional_count = 1
    # 通常のオプション・引数
    for a in parser._actions:
        # 排他グループで既に処理済みならスキップ
        if any(opt in exclusive_opts for opt in a.option_strings):
            continue

        if isinstance(a, argparse._SubParsersAction):
            # サブコマンド
            subcmds = list(a.choices.keys())
            args_lines.append(f"'1: :->subcmd'")
            # 再帰的に各サブコマンドの補完関数を生成
            for action in a._choices_actions:
                action: argparse.Action = action
                sub_name = action.dest
                sub_help = action.help
                sub_parser = a.choices[sub_name]
                sub_func = generate_zsh_completion(
                    sub_parser, f"{prog_name}_{sub_name}", level + 1
                )
                state_cases.append((sub_name, sub_func, sub_help))
        elif a.option_strings:
            # オプション引数
            if len(a.option_strings) == 1:
                opts = a.option_strings[0]
            else:
                opts = "{" + ",".join(a.option_strings) + "}"
            if a.nargs in [argparse.OPTIONAL, None]:
                if a.metavar or a.dest:
                    args_lines.append(
                        f"{opts}'[{a.help or ''}]:{a.metavar or a.dest}:_files'"
                    )
                else:
                    args_lines.append(f"{opts}'[{a.help or ''}]'")
            else:
                args_lines.append(f"{opts}'[{a.help or ''}]'")
        else:
            # 位置引数
            name = a.metavar or a.dest
            position = positional_count
            positional_count += 1
            choise = "(" + " ".join(a.choices) + ")" if a.choices else "_files"
            args_lines.append(f"'{position}:{name}:{choise}'")

    # 可変長引数の例
    args_lines.append("'*:: :->args'")

    # _arguments 出力
    lines.append("  _arguments -C \\")
    for arg_line in args_lines:
        lines.append(indent(f"{arg_line} \\", "    "))
    lines[-1] = lines[-1].rstrip(" \\")  # 最後の行のバックスラッシュを削除

    # サブコマンドの説明リスト
    if state_cases:
        lines.append("")
        lines.append("  subcommand=(")
        for sub_name, _, sub_help in state_cases:
            lines.append(f"    '{sub_name}:{sub_help}' \\")
        lines.append("  )")

    # 状態遷移 case
    if state_cases:
        lines.append("")
        lines.append("  case $state in")
        lines.append("    subcmd)")
        lines.append("      _describe '' subcommand")
        lines.append("      ;;")
        lines.append("    args)")
        lines.append("      case $words[1] in")
        for sub_name, _, _ in state_cases:
            lines.append(f"        {sub_name})")
            lines.append(f"          _{prog_name}_{sub_name}")
            lines.append("          ;;")
        lines.append("      esac")
        lines.append("      ;;")
        lines.append("  esac")

    lines.append("}")

    # サブコマンド補完関数を後ろに追加
    for _, sub_func, _ in state_cases:
        lines = [sub_func] + lines

    if level == 0:
        lines = (
            [f"#compdef {prog_name}"] + lines + [f"\ncompdef _{prog_name} {prog_name}"]
        )

    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_completion.py <path_to_cli> <bash|zsh>")
        sys.exit(1)

    path, shell = sys.argv[1:3]
    parser = load_parser_safely(path)
    prog = os.path.basename(path).replace(".py", "")

    if shell == "bash":
        with open(f"{prog}_completion.bash", "w") as f:
            f.write(generate_bash_completion(parser, prog))
    elif shell == "zsh":
        with open(f"_{prog}", "w") as f:
            f.write(generate_zsh_completion(parser, prog))
    else:
        print("Error: shell must be 'bash' or 'zsh'")
        sys.exit(1)


if __name__ == "__main__":
    main()
