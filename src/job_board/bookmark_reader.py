#!/usr/bin/env python3

import json
from pathlib import Path
from typing import List, Dict, Any

class BookmarkReader:

    def __init__(self, book_marks_path: Path, folder_path: str = '', recursive: bool = True):
        '''
        Docstring for __init__
        
        :param self: Description
        :param book_marks_path: path to bookmarks file
            :type book_marks_path: Path
        :param folder_path: Path within bookmarks to read
            :type folder_path: str
        :param recursive: Description
            :type recursive: bool
        '''
        self.bookmarks_path = book_marks_path
        self.folder_path = folder_path
        self.recursive = recursive

    def main(self):
    
        bookmarks_path = self.bookmarks_path
        bookmarks = self.load_bookmarks(bookmarks_path)

        folder_path = [p for p in self.folder_path.split("/") if p]

        roots = bookmarks["roots"]
        for root in roots.values():
            folder = self.find_folder_by_path(root, folder_path)
            if folder:
                return self.collect_urls(folder, recursive=not self.recursive)

        raise ValueError(f"Folder '{self.folder_path}' not found in bookmarks")

    def find_folder_by_path(self, 
        node: Dict[str, Any], path_parts: List[str]
    ):
        """
        Recursively find a folder by path, e.g. ["Job-searching", "jobs"]
        """
        if not path_parts:
            return node

        if node.get("type") != "folder":
            return None

        next_name = path_parts[0]
        for child in node.get("children", []):
            if child.get("type") == "folder" and child.get("name") == next_name:
                return self.find_folder_by_path(child, path_parts[1:])

        return None


    def collect_urls(self, folder: Dict[str, Any], recursive: bool = True) -> List[str]:
        """Collect URLs from a folder."""
        urls = []

        for child in folder.get("children", []):
            if child.get("type") == "url":
                urls.append(child["url"])
            elif recursive and child.get("type") == "folder":
                urls.extend(self.collect_urls(child, recursive=True))

        return urls


    def load_bookmarks(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)





if __name__ == "__main__":
    cls = BookmarkReader()
    urls = cls.main()
    print("\n".join(urls))
