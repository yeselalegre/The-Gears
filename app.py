from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# ==========================
# 🔹UPLOAD SETTINGS
# ==========================
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "mov", "avi", "webm"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ==========================
# 🔹DATABASE INITIALIZATION
# ==========================
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            photographer TEXT,
            content TEXT,           -- Headline
            content_text TEXT,      -- Full article body ✅
            category TEXT,
            media TEXT,
            date TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            name TEXT,
            comment TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()

# ==========================
# 🔹ADMIN DASHBOARD PAGE (with category filter)
# ==========================
@app.route("/admin")
def admin_dashboard():
    category = request.args.get("category")  # kunin yung category sa URL (hal. /admin?category=News)

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # 📊 Total counts
    cur.execute("SELECT COUNT(*) FROM articles")
    total_articles = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM comments")
    total_comments = cur.fetchone()[0]

    # 🗂️ Kuhanin lahat ng unique categories para sa dropdown
    cur.execute("SELECT DISTINCT category FROM articles ORDER BY category ASC")
    categories = [row[0] for row in cur.fetchall() if row[0]]

    # 📰 Kunin lahat ng article o filtered by category
    if category:
        cur.execute("SELECT id, title, category, date FROM articles WHERE category = ? ORDER BY id DESC", (category,))
    else:
        cur.execute("SELECT id, title, category, date FROM articles ORDER BY id DESC")

    articles = cur.fetchall()
    conn.close()

    return render_template(
        "admin.html",
        total_articles=total_articles,
        total_comments=total_comments,
        categories=categories,
        articles=articles,
        category=category or "All"
    )


# ==========================
# 🔹ADMIN PUBLISH PAGE (Add Article)
# ==========================
@app.route("/admin/publish", methods=["GET", "POST"])
def admin_publish():
    if request.method == "POST":
        title = request.form["title"]
        photographer = request.form["photographer"]
        content = request.form["content"]           # Headline
        content_text = request.form["content_text"] # ✅ Main article text
        category = request.form["category"]

        # ✅ Handle multiple file uploads
        files = request.files.getlist("files[]")
        media_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                media_paths.append(f"uploads/{filename}")

        # Combine all media paths
        media_path = ",".join(media_paths) if media_paths else None

        date = datetime.now().strftime("%B %d, %Y")

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO articles (title, photographer, content, content_text, category, media, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, photographer, content, content_text, category, media_path, date),
        )
        conn.commit()
        conn.close()

        return '<script>alert("✅ Article published successfully!"); window.location="/admin/publish";</script>'

    categories = ["News", "Updates", "Opinion", "Feature", "Literary", "Komiks", "Arts", "Photos", "Videos"]
    return render_template("publish.html", categories=categories)


# ==========================
# 🔹USER PAGE (List Articles + Search by Keyword)
# ==========================
@app.route("/user")
def user():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "All")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # 🧠 Base query
    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    # 🔍 Search in headline (content) or article body (content_text)
    if search:
        query += " AND (LOWER(content) LIKE ? OR LOWER(content_text) LIKE ?)"
        params.extend((f"%{search.lower()}%", f"%{search.lower()}%"))

    # 🗂️ Optional category filter
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY id DESC"
    cur.execute(query, params)
    articles = cur.fetchall()
    conn.close()

    # ✅ Render page with search + category context
    return render_template(
        "user.html",
        articles=articles,
        search=search,
        category=category
    )


# ==========================
# 🔹ARTICLE VIEW (with comments)
# ==========================
@app.route("/article/<int:id>", methods=["GET", "POST"])
def article_view(id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    article = cur.execute("SELECT * FROM articles WHERE id=?", (id,)).fetchone()
    if not article:
        return "Article not found", 404

    # ✅ Handle comments
    if request.method == "POST":
        name = request.form.get("name", "Anonymous") or "Anonymous"
        comment = request.form["comment"]
        date = datetime.now().strftime("%B %d, %Y %I:%M %p")
        cur.execute(
            "INSERT INTO comments (article_id, name, comment, date) VALUES (?, ?, ?, ?)",
            (id, name, comment, date),
        )
        conn.commit()

    comments = cur.execute(
        "SELECT name, comment, date FROM comments WHERE article_id=? ORDER BY id DESC", (id,)
    ).fetchall()

    # ✅ Split media paths for carousel
    media_files = article[6].split(",") if article[6] else []
    media_paths = [f"/static/{path}" for path in media_files]

    conn.close()

    return render_template("article_view.html", article=article, media_paths=media_paths, comments=comments)


# ==========================
# 🔹HOME REDIRECT
# ==========================
@app.route("/")
def home():
    return redirect(url_for("user"))


# ==========================
# 🔹RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(debug=True)
