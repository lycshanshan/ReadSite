# Change Log

## [0.3.4] 2026-04-04

### What's New
- Optimized the Reco system, now a user can only vote 4 Recos to a book in one day.
- Optimized the Reco experience, now users can vote multiple Recos once.

### Bug Fixes
- Fixed the N+1 query problem in `my_bookshelf` view.
- Fixed the Reco display bug after checkin.

### Improvements
- Optimized the style of the confirm-download modal.
- Changed Django language to `zh-hans`.
- Changed Django time zone to `UTC+8`.

### Future Features
- [x] Optimize Reco system.
- [ ] Custom order criteria, filters and book groups.

## [0.3.3] 2026-04-02

### Bug Fixes
- Fixed the bug that `reco` field of `Book` can be changed by staff in `/admin` page. ([Issue #8](https://github.com/lycshanshan/ReadSite/issues/8))

### Improvements
- Change the `user_level` field of `UserPoints` to a property, tying to `exp`.

### Future Features
- [ ] Optimize Reco system.
- [ ] Custom order criteria, filters and book groups.

## [0.3.2] 2026-03-24

### What's New
- Now the Recos of a book can be shown on the index page.
- Add `batch-download` API method, it accepts a list parameter and returns a `.zip` file.

### Bug Fixes
- Fixed the duplicate and choose-more-than-4-books problem of the Reco system.
- Fixed the API docs problem that book-download can't run on the doc site.
- Fixed the type warning in `serializers.py`.

### Improvements
- Optimized the `book_detail.html` code.

### Future Features
- [ ] Optimize Reco system.
- [ ] Custom order criteria, filters and book groups.

## [0.3.1] 2026-03-23

### Bug Fixes
- Fixed some bugs caused by merge.

### Improvements
- Changed the Reco system language to Chinese.
- Modified comments.

### Future Features
- [ ] Optimize Reco system.
- [ ] Custom order criteria, filters and book groups.

## [0.3.0] 2026-03-22

### What's New
- Reconstructed the database from `SQLite` to `MySQL`.

### Future Features
- [x] Reconstruct the database from `SQLite` to `MySQL`.
- [ ] Custom order criteria, filters and book groups.
- [x] Recommendation system.

### * How to change your database from `SQLite` to `MySQL`?
1. Run the following command to save your sqlite data to a json file:
```bash
python -X utf8 manage.py dumpdata datadump.json
```
If you encounter a problem when importing it to MySQL, try to use this:
```bash
python -X utf8 manage.py dumpdata reader.Tag reader.Book reader.Chapter reader.Illustration reader.UserProgress reader.Bookshelf reader.Bookmark reader.GlobalSettings reader.UserPoints reader.StaffApplication auth.user --exclude contenttypes --exclude auth.permission --natural-foreign --output datadump.json
```
2. Create a MySQL database and change your `.env` file. (You can refer to [README](README.md))
3. Run the following command to migrate data:
```bash
python manage.py loaddata datadump.json
```

## [0.2.1] 2026-03-22

### What's New
- Updated administrator page.
  - Use `django-jazzmin` to beautify admin page.
  - Now staffs can view the admin page to view all `Book`, `Chapter`, `Illustration`, `Tag`, while they can only modify what they uploaded; they can only add `Tag`.
- When normal user try to view `/admin`, redirect them to `joinus.html`, they can submit application to become staff.
- Author label can now be clicked to search for books witten by the same author. (By [@JIMJMjm](https://github.com/JIMJMjm))

### Bug Fixes
- Fixed some inconsistent appearance in `book_detail.css` (By [@JIMJMjm](https://github.com/JIMJMjm))

### Future Features
- [ ] Reconstruct the database from `SQLite` to `MySQL`.
- [ ] Custom order criteria, filters and book groups.
- [x] Recommendation system.

## [0.2.0] 2026-03-22

### What's New
- Recommendation system is now available. Users can aquire `Recos` through daily check-in and use them to recommend a book in its detail page.
- The display of recommended book on title page has a revamped logic.

### Bug Fixes
- Fixed `UserPoint not exist` when trying to download books via a pre-registed User.

### Improvements
- Added `library` link to book detail page.

### Future Features
- [ ] Custom order criteria, filters and book groups.
- [x] Recommendation system.

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