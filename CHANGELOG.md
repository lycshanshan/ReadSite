# Change Log

## [0.1.1] 2026-03-18

### What's New
- Created `Tags` model for storing all tags.
- Change `Book.tags` model from `JSONField` to `ManyToManyField`.
- Tags are now displayed in library, with a maximun of 4 tags per book.
- Title widgets on "book_detail" page can now be clicked as Home button.
- Buttons under the book widgets are added to quickly manage user bookshelf.
- Tags are now displayed under the title in detail pages.

### Bug Fixes
- Fixed the API document page.
- Fixed "Not Found /favicon.ico 404" state by addding a `favicon.ico` to `/static`.

### Improvements
- The book description of `book_detail` page now has the indent of `2em`.
- Link logic between detail page and library is more clear.
- Button "TXT下载" now possesses a better color.
- Other improvements speading in `*.css` and `element-style`.

### Future Features
- [ ] Set a maximum for tags of each book.
- [ ] Custom order criteria, filters and book groups.
- [ ] Recommendation system.