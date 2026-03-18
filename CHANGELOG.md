# Change Log

## [0.1.1] 2026-03-18

### What's New
- Tags are now displayed in library, with a maximun of 4 tags per book.
- Title widgets on "book_detail" page can now be clicked as Home button.
- Buttons under the book widgets are added to quickly manage user bookshelf.

### Bug Fixes
- `JSONField` is no longer a `string` in api documents, serializers and in practice.
- Fixed "Not Found /favicon.ico 404" state by addding a `favicon.ico` to `/static`.

### Improvements
- The book description of `book_detail` page now has the indent of `2em`.
- Link logic between detail page and library is more clear.
- Other improvements speading in `*.css`.

### Future Features
- [ ] Search by certain tag(s) or/and author. 
- [ ] Custom order criteria, filters and book groups.
- [ ] Recommendation system.