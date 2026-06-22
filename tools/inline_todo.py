#!/usr/bin/env python3
from re import compile
from os import walk, path
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from argparse import ArgumentParser

@dataclass
class Todo:
    file: str
    line: int
    tags: List[str]
    content: str
    date: Optional[date]


class TagList(dict):

    def add_todo(self, todo: Todo) -> None:
        for tag in todo.tags:
            if tag not in self:
                self[tag] = []
            self[tag].append(todo)

    def get_todos(self, *tags) -> List[Todo]:
        out = []
        for tag in tags:
            out += self.get([tag], [])
        return out


class InlineTodo:

    def __init__(
            self,
            source_directory: str,
            out_file: str,
            by_urgency: bool = True,
            by_file: bool = True,
            by_tags: bool = False,
            show_total: bool = True,
            external_todo: Optional[str] = 'Todo.md'
        ):
        self.source_directory: str = source_directory
        self.out_file = out_file
        self.todos: List[Todo] = []
        self.tags_list: TagList = TagList()
        self.by_urgency: bool = by_urgency
        self.by_file: bool = by_file
        self.by_tags: bool = by_tags
        self.show_total: bool = show_total
        self.external_todo: Optional[str] = external_todo

    def parse(self) -> None:
        todo_pattern = compile(r'# TODO:(?P<tags>(?:\w+:)*)\s*(?P<content>.*?)$')
        date_pattern = compile(r'(?P<date>\d{4}-\d{2}-\d{2})')
        content_pattern = compile(r'# TODO:(?:\w+:\s*)?(.*)$')

        # Traverse the source directory and collect TODO comments
        for root, dirs, files in walk(self.source_directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = path.join(root, file)
                    with open(file_path, 'r') as f:
                        for line_number, line in enumerate(f, start=1):
                            match = todo_pattern.search(line)
                            if match:
                                tags: List[str] = match.group('tags').strip(' :').split(':') if match.group('tags') else []
                                content: str = match.group('content')
                                date_match = date_pattern.search(content)
                                try:
                                    the_date = date.fromisoformat(date_match.group('date')) if date_match else None  # None means far in the future
                                except Exception as e:
                                    print(f'error in date: {file_path}:{line_number}: {date_match.group("date")}')
                                    the_date = None
                                todo = Todo(file=file_path, line=line_number, tags=tags, content=content, date=the_date)
                                self.todos.append(todo)
                                self.tags_list.add_todo(todo)


    def write_index(self, f) -> None:
        # Write the index
        f.write('## Index\n')
        if self.by_urgency:
            f.write('- [Urgent](#urgent)\n')
        if self.by_file:
            f.write('- [By File](#by-file)\n')
        if self.by_tags:
            f.write('- [By Tags](#by-tags)\n')
        if self.external_todo and Path(self.external_todo).is_file():
            f.write(f'- [External Todo]({self.external_todo})\n')

    def write_by_urgent(self, f) -> None:
        f.write('\n## Urgent\n')
        # Sort the todos by urgency (date) and then by file name
        self.todos.sort(key=lambda x: (x.date or date(2099, 12, 31), x.file))
        current_date = ''
        for todo in self.todos:
            if todo.date != current_date:
                current_date = todo.date
                f.write(f"\n### {current_date if current_date else 'No time constraint'}\n")
            f.write(f"- `{todo.file}:{todo.line}`\n")
            tags_str = ' '.join([f'**#{tag}**' for tag in todo.tags])
            if len(tags_str) > 0:
                tags_str += ' '
            f.write(f"  {tags_str}{todo.content.strip()}\n")

    def write_by_file(self, f) -> None:
        f.write('\n## By File\n')
        current_file = ''
        for todo in sorted(self.todos, key=lambda x: (x.file, x.line)):
            if todo.file != current_file:
                current_file = todo.file
                f.write(f"\n### `{todo.file}`\n")
            tags_str = ' '.join([f'**#{tag}**' for tag in todo.tags])
            if len(tags_str) > 0:
                tags_str += ' '
            f.write(f"- Line {todo.line}: {todo.date} {tags_str}\n")
            f.write(f"  {todo.content.strip()}\n")

    def write_by_tags(self, f) -> None:
        f.write('\n## By Tags\n')
        tags = list(self.tags_list.keys())
        tags.sort(key=lambda x: len(self.tags_list[x]), reverse=True)
        for tag in tags:
            if len(self.tags_list[tag]) > 0:
                f.write(f'\n### **#{tag}**\n')
                for todo in self.tags_list.get(tag, []):
                    f.write(f"- `{todo.file}:{todo.line}`{' (' + todo.date + ')' if todo.date else ''}\n")
                    f.write(f"  {todo.content.strip()}\n")

    def generate(self) -> None:
        # Generate the output file
        with open(self.out_file, 'w') as f:
            f.write('# Inline Todo\n\n')
            if self.show_total:
                f.write(f'Total: {len(self.todos)}\n\n')
            self.write_index(f)

            # Write the urgent list
            if self.by_urgency:
                self.write_by_urgent(f)

            # Write the list sorted by file name
            if self.by_file:
                self.write_by_file(f)

            # Write by Tags
            if self.by_tags:
                self.write_by_tags(f)


if __name__ == '__main__':
    parser = ArgumentParser(description='Parse TODO comments in source files')
    parser.add_argument('--source_directory', type=str, default='src', help='Specify the source directory (default: src)')
    parser.add_argument('--out_file', type=str, default='INLINE_TODO.md', help='Specify the output file name (default: INLINE_TODO.md)')
    parser.add_argument('--xfile', dest='by_file', action='store_false', default=True, help="Don't show file list")
    parser.add_argument('--xurgency', dest='by_urgency', action='store_false', default=True, help="Don't show list by date")
    parser.add_argument('--tags', dest='by_tags', action='store_true', default=False, help='Show list by tags')
    parser.add_argument('--xtotal', dest='show_total', action='store_false', default=True, help="Don't display total count of TODOs ")
    parser.add_argument('--external_todo', type=str, default='Todo.md', help='Specify the external TODO file (default: Todo.md)')

    args = parser.parse_args()
    inline_todo = InlineTodo(
        args.source_directory, args.out_file, args.by_urgency, args.by_file, args.by_tags,
        args.show_total, args.external_todo
    )
    inline_todo.parse()
    inline_todo.generate()
