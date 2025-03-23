import sqlite3
from pathlib import Path
import subprocess
import shutil
import pymupdf
import sys


def main():
    backup_dir = Path('/home/pokerfacowaty/kobo backup 23.03.2025')
    dot_kobo_dir = backup_dir / '.kobo'
    db_file = dot_kobo_dir / 'KoboReader.sqlite'
    markups_folder = dot_kobo_dir / 'markups'
    combined_markups_foder = Path(__file__).parent.resolve() / 'markups_combined'
    last_update = '2025-03-01',

    get_nonpdf_markups(db_file, last_update, markups_folder,
                       combined_markups_foder)
    get_pdf_ink_annotations(backup_dir, combined_markups_foder)


def get_nonpdf_markups(db_file, last_update, markups_folder,
                       combined_markups_folder):
    connection = sqlite3.connect(db_file)
    # connection.text_factory = lambda b: b.decode(errors='ignore')
    cur = connection.cursor()
    response = cur.execute('SELECT BookmarkID, VolumeID FROM Bookmark'
                           + 'WHERE Type = "markup" AND DateModified > ?',
                           last_update)
    non_pdf_bookmark_data = response.fetchall()
    existing = 0

    book_titles = {}
    for i, _ in enumerate(non_pdf_bookmark_data):
        # For testing
        if (sys.argv[1] == 'skipnonpdf'):
            break
        bookmark_id = non_pdf_bookmark_data[i][0]
        book_id = non_pdf_bookmark_data[i][1],

        if book_titles.get(book_id, False):
            book_title = book_titles[book_id]
        else:
            response = cur.execute('SELECT BookTitle FROM content'
                                   + 'WHERE BookId = ? LIMIT 1', book_id)
            book_title = response.fetchone()[0]
            book_title = book_title.replace('/', '_')
            book_titles[book_id] = book_title

        # Skipping getting the author for now
        svg_path = markups_folder / (bookmark_id + '.svg')
        jpg_path = markups_folder / (bookmark_id + '.jpg')

        book_dir = book_title
        markup_filename = bookmark_id + '.jpg'

        final_markup_dir = combined_markups_folder / book_dir
        final_markup_path = final_markup_dir / markup_filename

        if final_markup_path.exists():
            print(f'[LOG] File exists: {markup_filename}, skipping...')
            existing += 1
            continue
        Path.mkdir(final_markup_dir, exist_ok=True)
        ffmpeg_args = [shutil.which('ffmpeg'), '-hide_banner', '-loglevel',
                       'error', '-y', '-i', jpg_path, '-i', svg_path,
                       '-filter_complex', "'overlay'", final_markup_path]
        subprocess.Popen(ffmpeg_args)
    print(existing)


def get_pdf_ink_annotations(backup_dir, combined_markups_folder):
    # FIXME: Doesn't care about last_updated date, gets all annotations
    pdf_paths = []
    for dirpath, _, filenames in backup_dir.walk():
        for fname in filenames:
            if fname.endswith('pdf'):
                pdf_paths.append(dirpath / fname)
    print(pdf_paths)

    for pdf_path in pdf_paths:
        doc = pymupdf.open(pdf_path)
        zoom_x = 3.0
        zoom_y = 3.0
        mat = pymupdf.Matrix(zoom_x, zoom_y)

        for pageNum, page in enumerate(doc):
            if page.first_annot:
                pix = page.get_pixmap(matrix=mat)
                final_markup_dir = combined_markups_folder / pdf_path.stem
                print(final_markup_dir)
                Path.mkdir(final_markup_dir, exist_ok=True)
                pix.save(final_markup_dir / f'{pageNum + 1}.jpg')


if __name__ == '__main__':
    main()
