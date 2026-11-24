# my_toa_lib

Two TOA libraries, published here for demonstrations of the TOA preview. This repository is temporary.

TOA (True-OpenAccess) is a draft standard for circuit design objects: <https://github.com/true-openaccess/toa>. Neither the standard nor these libraries have a release yet.

| Branch | Library | Objects | Process | Licence |
|---|---|---|---|---|
| [`pll`](../../tree/pll) | The PLL of rnl-gallery: 81 interfaces, 81 circuits and a frozen library | 163 | `tsmc180` | CC0-1.0 |
| [`risca`](../../tree/risca) | RISCA, exported from Virtuoso with toa-virtuoso: 33 interfaces, 33 circuits and a frozen library | 67 | `tsmc28` | CC-BY-4.0 |

Each branch is a library on its own: its publication branch is that branch, and `library.source.jsonl` at its top lists its objects. The models of the devices and the libraries of the processes are not included.

To include both in a workspace list:

```json
{"toa": "source/1"}
{"include": "library.source.jsonl", "group": "pll", "branch": "pll", "sources": [{"git": "https://github.com/many-question/my_toa_lib.git"}]}
{"include": "library.source.jsonl", "group": "risca", "branch": "risca", "sources": [{"git": "https://github.com/many-question/my_toa_lib.git"}]}
```

They can be browsed with Gazettoa, a read-only browser for TOA libraries: <https://true-openaccess.github.io/gazettoa/>.
