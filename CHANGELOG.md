# Change Log

## [0.1.2] 2026-03-20

### What's New
- A book can now only bound to 6 tags.
- Changed book_download view & API view, now a book with illustrations will be downloaded as a .zip file.

### Bug Fixes
- Fixed the CSRF-verification error caused by `settings.py` on server.

### Improvements
- Added `我的书架` link to library page.

### Future Features
- [x] Set a maximum for tags of each book.
- [ ] Custom order criteria, filters and book groups.
- [ ] Recommendation system.