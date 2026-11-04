import os
import sys
import urllib.parse
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "agri-secret-production-key-2026")

class VercelPathMiddleware:
    """Restores the original requested URI on Vercel serverless rewrites."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        forwarded_uri = (
            environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("HTTP_X_MATCHED_PATH")
            or environ.get("HTTP_X_ORIGINAL_URL")
        )
        if forwarded_uri:
            environ["PATH_INFO"] = forwarded_uri.split("?")[0]
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

def get_db_config():
    """Extract database connection settings from DATABASE_URL, POSTGRES_URL, or discrete environment variables."""
    raw_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("POSTGRES_URL_NON_POOLING")
        or os.environ.get("POSTGRES_PRISMA_URL")
    )
    if raw_url:
        db_url = raw_url.strip().strip('"').strip("'")
        parsed = urllib.parse.urlparse(db_url)
        config = {
            "dbname": parsed.path.lstrip("/") or "postgres",
            "user": parsed.username or "postgres",
            "password": urllib.parse.unquote(parsed.password or ""),
            "host": parsed.hostname,
            "port": parsed.port or 5432,
        }
        qs = urllib.parse.parse_qs(parsed.query)
        if "sslmode" in qs:
            config["sslmode"] = qs["sslmode"][0]
        elif parsed.hostname not in ("localhost", "127.0.0.1", None):
            # Cloud databases (Neon, Supabase, Vercel Postgres, AWS RDS) require SSL
            config["sslmode"] = "require"
        return config
    else:
        return dict(
            dbname=os.environ.get("DB_NAME", "SmartAgricultureDB"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", ""),
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", 5432)),
        )

# Serverless-friendly connection manager with active liveness check and retry
_conn = None

def get_connection():
    global _conn
    config = get_db_config()
    try:
        if _conn is not None and not _conn.closed:
            # Quick ping to verify connection socket is alive (prevents stale serverless socket errors)
            with _conn.cursor() as cur:
                cur.execute("SELECT 1")
            return _conn
    except Exception:
        reset_connection()

    _conn = psycopg2.connect(**config, connect_timeout=10)
    return _conn

def reset_connection():
    global _conn
    if _conn is not None:
        try:
            if not _conn.closed:
                _conn.close()
        except Exception:
            pass
    _conn = None

def q(query, args=(), fetch=True):
    """Executes a query safely with automatic reconnection on dropped serverless connections."""
    for attempt in range(2):
        try:
            con = get_connection()
            with con:
                with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, args)
                    return cur.fetchall() if fetch else None
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            reset_connection()
            if attempt == 1:
                raise

def init_tables_if_needed():
    """Checks if the database is newly connected and initializes schema and seed data automatically."""
    try:
        check = q("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='farmer'")
        if not check:
            schema_file = os.path.join(BASE_DIR, "schema.sql")
            seed_file = os.path.join(BASE_DIR, "seed.sql")
            con = get_connection()
            with con:
                with con.cursor() as cur:
                    if os.path.exists(schema_file):
                        with open(schema_file, "r", encoding="utf-8") as f:
                            cur.execute(f.read())
                    if os.path.exists(seed_file):
                        with open(seed_file, "r", encoding="utf-8") as f:
                            cur.execute(f.read())
    except Exception as e:
        print(f"Auto-init check note: {e}")

# Table metadata: table -> (title, primary key, [(column, input type)], {fk column: (table, label column)})
T = {
    "farmer": ("Farmers", "farmer_id", [("name","text"),("phone","text"),("address","text")], {}),
    "field": ("Fields", "field_id", [("farmer_id","fk"),("field_name","text"),("area","number"),("location","text")], {"farmer_id":("farmer","name")}),
    "soil": ("Soil tests", "soil_id", [("field_id","fk"),("test_date","date"),("soil_type","text"),("ph","number"),("nitrogen","number"),("phosphorus","number"),("potassium","number"),("moisture","number")], {"field_id":("field","field_name")}),
    "crop": ("Crops", "crop_id", [("crop_name","text"),("crop_type","text"),("min_ph","number"),("max_ph","number"),("water_requirement","text"),("min_nitrogen","number"),("min_phosphorus","number"),("min_potassium","number")], {}),
    "crop_season": ("Crop seasons", "crop_season_id", [("crop_id","fk"),("season","text")], {"crop_id":("crop","crop_name")}),
    "field_crop": ("Field crops", "field_crop_id", [("field_id","fk"),("crop_id","fk"),("season","text"),("sowing_date","date"),("harvest_date","date"),("yield","number")], {"field_id":("field","field_name"),"crop_id":("crop","crop_name")}),
    "weather": ("Weather", "weather_id", [("field_id","fk"),("date","date"),("temperature","number"),("rainfall","number"),("humidity","number")], {"field_id":("field","field_name")}),
    "irrigation": ("Irrigation", "irrigation_id", [("field_id","fk"),("date","date"),("water_amount","number"),("method","text")], {"field_id":("field","field_name")}),
    "fertilizer": ("Fertilizers", "fertilizer_id", [("fertilizer_name","text"),("type","text"),("nitrogen_content","number"),("phosphorus_content","number"),("potassium_content","number")], {}),
    "field_fertilizer": ("Fertilizer use", "field_fertilizer_id", [("field_id","fk"),("fertilizer_id","fk"),("date","date"),("quantity","number")], {"field_id":("field","field_name"),"fertilizer_id":("fertilizer","fertilizer_name")}),
    "recommendation": ("Recommendations", "recommendation_id", [("field_id","fk"),("crop_id","fk"),("fertilizer_id","fk"),("recommendation_date","date"),("irrigation_advice","text"),("reason","text")], {"field_id":("field","field_name"),"crop_id":("crop","crop_name"),"fertilizer_id":("fertilizer","fertilizer_name")}),
}

@app.context_processor
def nav():
    return dict(tables=T)

def options(table, label):
    if table not in T:
        return []
    pk = T[table][1]
    query = sql.SQL('SELECT {pk} AS id, {lbl} AS label FROM {tbl} ORDER BY {pk}').format(
        pk=sql.Identifier(pk),
        lbl=sql.Identifier(label),
        tbl=sql.Identifier(table)
    )
    return q(query)

def fk_lookup(t):
    if t not in T:
        return {}
    return {c: {r["id"]: r["label"] for r in options(*T[t][3][c])} for c in T[t][3]}

def next_id(t):
    if t not in T:
        return 1
    pk = T[t][1]
    query = sql.SQL('SELECT COALESCE(MAX({pk}), 0) + 1 AS n FROM {tbl}').format(
        pk=sql.Identifier(pk),
        tbl=sql.Identifier(t)
    )
    res = q(query)
    return res[0]["n"] if res else 1

@app.route("/")
def dashboard():
    try:
        init_tables_if_needed()
        counts = {t: q(sql.SQL('SELECT COUNT(*) AS c FROM {tbl}').format(tbl=sql.Identifier(t)))[0]["c"] for t in T}
        area_res = q("SELECT COALESCE(SUM(area), 0) AS a FROM field")
        area = area_res[0]["a"] if area_res else 0
        yields = q("""SELECT c.crop_name, ROUND(AVG(fc.yield), 0) AS y 
                      FROM crop c 
                      JOIN field_crop fc ON c.crop_id=fc.crop_id 
                      GROUP BY c.crop_name 
                      ORDER BY y DESC""")
        recent = q("""SELECT fl.field_name, c.crop_name, r.recommendation_date 
                      FROM recommendation r
                      JOIN field fl ON r.field_id=fl.field_id 
                      LEFT JOIN crop c ON r.crop_id=c.crop_id
                      ORDER BY r.recommendation_date DESC LIMIT 5""")
        
        yield_values = [float(y["y"]) for y in yields if y.get("y") is not None and float(y["y"]) > 0]
        top_yield = max(yield_values) if yield_values else 1.0

        return render_template("index.html", counts=counts, area=area, yields=yields, recent=recent,
                               top=top_yield)
    except Exception as e:
        return render_template("setup.html", error=str(e)), 200

@app.route("/init-db", methods=["GET", "POST"])
def init_db():
    try:
        schema_file = os.path.join(BASE_DIR, "schema.sql")
        seed_file = os.path.join(BASE_DIR, "seed.sql")
        con = get_connection()
        with con:
            with con.cursor() as cur:
                if os.path.exists(schema_file):
                    with open(schema_file, "r", encoding="utf-8") as f:
                        cur.execute(f.read())
                if os.path.exists(seed_file):
                    with open(seed_file, "r", encoding="utf-8") as f:
                        cur.execute(f.read())
        flash("Database schema initialized and sample data seeded successfully!")
    except Exception as e:
        flash(f"Database initialization error: {e}")
    return redirect(url_for("dashboard"))

@app.route("/t/<t>")
def list_rows(t):
    if t not in T:
        flash(f"Table '{t}' does not exist.")
        return redirect(url_for("dashboard"))
    title, pk, cols, fks = T[t]
    query = sql.SQL('SELECT * FROM {tbl} ORDER BY {pk}').format(
        tbl=sql.Identifier(t),
        pk=sql.Identifier(pk)
    )
    rows = q(query)
    return render_template("list.html", t=t, title=title, pk=pk, cols=[c for c,_ in cols], rows=rows, lk=fk_lookup(t))

@app.route("/t/<t>/add", methods=["GET","POST"])
@app.route("/t/<t>/edit/<int:rid>", methods=["GET","POST"])
def form(t, rid=None):
    if t not in T:
        flash(f"Table '{t}' does not exist.")
        return redirect(url_for("dashboard"))
    title, pk, cols, fks = T[t]
    names = [c for c, _ in cols]
    if request.method == "POST":
        vals = [request.form.get(c) or None for c in names]
        try:
            if rid is None:
                new_id = next_id(t)
                insert_cols = [pk] + names
                query = sql.SQL('INSERT INTO {tbl} ({col_names}) VALUES ({placeholders})').format(
                    tbl=sql.Identifier(t),
                    col_names=sql.SQL(", ").join(sql.Identifier(c) for c in insert_cols),
                    placeholders=sql.SQL(", ").join(sql.Placeholder() for _ in insert_cols)
                )
                q(query, [new_id] + vals, fetch=False)
                flash(f"Record added to {title}.")
            else:
                set_clauses = [sql.SQL("{col} = %s").format(col=sql.Identifier(c)) for c in names]
                query = sql.SQL('UPDATE {tbl} SET {set_clause} WHERE {pk} = %s').format(
                    tbl=sql.Identifier(t),
                    set_clause=sql.SQL(", ").join(set_clauses),
                    pk=sql.Identifier(pk)
                )
                q(query, vals + [rid], fetch=False)
                flash(f"Record in {title} updated.")
            return redirect(url_for("list_rows", t=t))
        except psycopg2.Error as e:
            err_msg = e.pgerror.splitlines()[0] if e.pgerror else str(e)
            flash(f"Could not save: {err_msg}")

    row = {}
    if rid is not None:
        select_query = sql.SQL('SELECT * FROM {tbl} WHERE {pk} = %s').format(
            tbl=sql.Identifier(t),
            pk=sql.Identifier(pk)
        )
        found = q(select_query, (rid,))
        if not found:
            flash(f"Record with ID {rid} was not found.")
            return redirect(url_for("list_rows", t=t))
        row = found[0]

    opts = {c: options(*fks[c]) for c in fks}
    return render_template("form.html", t=t, title=title, cols=cols, row=row, opts=opts, editing=rid is not None)

@app.post("/t/<t>/delete/<int:rid>")
def delete(t, rid):
    if t not in T:
        flash(f"Table '{t}' does not exist.")
        return redirect(url_for("dashboard"))
    try:
        delete_query = sql.SQL('DELETE FROM {tbl} WHERE {pk} = %s').format(
            tbl=sql.Identifier(t),
            pk=sql.Identifier(T[t][1])
        )
        q(delete_query, (rid,), fetch=False)
        flash("Record deleted.")
    except psycopg2.IntegrityError:
        flash("Cannot delete: other records still depend on this one. Delete or reassign those first.")
    except psycopg2.Error as e:
        err_msg = e.pgerror.splitlines()[0] if e.pgerror else str(e)
        flash(f"Delete failed: {err_msg}")
    return redirect(url_for("list_rows", t=t))

# ---------- Smart Agricultural Advisor (Soil + Weather + Seasonality + Nutrients) ----------
LEVELS = {"Low": 0, "Medium": 1, "High": 2}

def get_current_season():
    """Identifies the ongoing agricultural crop season."""
    m = date.today().month
    if 6 <= m <= 10:
        return "Kharif"
    elif m in (11, 12, 1, 2):
        return "Rabi"
    else:
        return "Summer"

def advise(field_id):
    soil = q("SELECT * FROM soil WHERE field_id=%s ORDER BY test_date DESC LIMIT 1", (field_id,))
    if not soil:
        return None
    s = soil[0]

    crops = q("SELECT * FROM crop")
    if not crops:
        return None

    current_season = get_current_season()
    seasons_data = q("SELECT crop_id, season FROM crop_season")
    crop_seasons = {}
    for row in seasons_data:
        crop_seasons.setdefault(row["crop_id"], set()).add(row["season"])

    moisture = float(s["moisture"] or 0)
    level = 2 if moisture >= 55 else 1 if moisture >= 40 else 0
    ph = float(s["ph"] or 7.0)

    scored_crops = []
    for c in crops:
        score = 0.0
        min_ph = float(c["min_ph"]) if c.get("min_ph") is not None else 5.5
        max_ph = float(c["max_ph"]) if c.get("max_ph") is not None else 7.5

        # 1. pH suitability
        if min_ph <= ph <= max_ph:
            score += 3.0
        elif abs(ph - min_ph) <= 0.5 or abs(ph - max_ph) <= 0.5:
            score += 1.0

        # 2. Water requirement matching
        c_req = (c.get("water_requirement") or "Medium").capitalize()
        req_level = LEVELS.get(c_req, 1)
        score += max(0.0, 2.0 - abs(req_level - level) * 1.0)

        # 3. Seasonal suitability
        supported = crop_seasons.get(c["crop_id"], set())
        if current_season in supported:
            score += 2.0
        elif not supported:
            score += 1.0

        scored_crops.append((score, c))

    scored_crops.sort(key=lambda x: x[0], reverse=True)
    best_score, best = scored_crops[0]
    alternatives = [c for _, c in scored_crops[1:3]]

    # Crop-specific nutrient deficit calculation
    targets = {
        "nitrogen": float(best.get("min_nitrogen") or 80),
        "phosphorus": float(best.get("min_phosphorus") or 45),
        "potassium": float(best.get("min_potassium") or 60),
    }

    def nutrient_ratio(n):
        val = float(s.get(n) or 0)
        tgt = targets.get(n, 50)
        return val / tgt if tgt > 0 else 1.0

    weak = min(targets, key=nutrient_ratio)
    weak_col = f"{weak}_content"

    fert_query = sql.SQL('SELECT * FROM fertilizer ORDER BY {col} DESC LIMIT 1').format(
        col=sql.Identifier(weak_col)
    )
    fert_rows = q(fert_query)
    fert = fert_rows[0] if fert_rows else {"fertilizer_id": None, "fertilizer_name": "Balanced NPK", "type": "Multi-nutrient"}

    # Weather context
    weather_rows = q("SELECT * FROM weather WHERE field_id=%s ORDER BY date DESC LIMIT 1", (field_id,))
    w = weather_rows[0] if weather_rows else None
    rain = float(w["rainfall"]) if w and w.get("rainfall") is not None else 0.0
    temp = float(w["temperature"]) if w and w.get("temperature") is not None else None

    if rain >= 15.0:
        irr = f"Recent rainfall ({rain:.1f} mm) is sufficient; hold off on active irrigation to prevent waterlogging."
    elif temp and temp >= 32.0:
        irr = f"High temperature ({temp:.1f}°C); irrigate early morning or evening to minimize evaporation."
    else:
        req = (best.get("water_requirement") or "Medium").capitalize()
        irr = {"High": "Irrigate frequently; this crop needs plenty of water.",
               "Medium": "Moderate irrigation; water when moisture drops below 40%.",
               "Low": "Light irrigation is enough."}.get(req, "Irrigate as needed.")

    reason_parts = [
        f"Soil test: pH {ph:.2f}, moisture {moisture:.1f}%.",
        f"{best['crop_name']} suits pH {best['min_ph']}-{best['max_ph']} and the {current_season} season.",
        f"{weak.title()} is the lowest nutrient relative to {best['crop_name']}'s needs, so {fert['fertilizer_name']} is suggested."
    ]
    if w:
        reason_parts.append(f"Latest weather: {w['temperature']}°C with {w['rainfall']} mm rainfall.")

    reason = " ".join(reason_parts)
    return dict(crop=best, fert=fert, irrigation=irr, reason=reason, soil=s, weather=w, alternatives=alternatives, season=current_season)

@app.route("/recommend", methods=["GET","POST"])
def recommend():
    try:
        fields = q("SELECT field_id, field_name FROM field ORDER BY field_id")
    except Exception as e:
        return render_template("setup.html", error=str(e)), 200

    result, fid = None, request.values.get("field_id")
    if fid:
        try:
            result = advise(int(fid))
            if result is None:
                flash("This field has no soil test yet, or crop data is missing. Add a soil test first.")
        except (ValueError, TypeError):
            flash("Invalid field selected.")
            fid = None

    if request.method == "POST" and request.form.get("save") and result:
        try:
            rec_id = next_id("recommendation")
            q("""INSERT INTO recommendation (recommendation_id, field_id, crop_id, fertilizer_id, recommendation_date, irrigation_advice, reason)
                 VALUES (%s,%s,%s,%s,%s,%s,%s)""",
              (rec_id, fid, result["crop"]["crop_id"], result["fert"]["fertilizer_id"],
               date.today(), result["irrigation"], result["reason"][:500]), fetch=False)
            flash("Recommendation saved successfully.")
            return redirect(url_for("list_rows", t="recommendation"))
        except psycopg2.Error as e:
            err_msg = e.pgerror.splitlines()[0] if e.pgerror else str(e)
            flash(f"Could not save recommendation: {err_msg}")

    return render_template("recommend.html", fields=fields, fid=fid, r=result)

@app.errorhandler(404)
def not_found(e):
    return render_template("setup.html", error="404 Not Found: The requested URL was not found on the server."), 404

@app.errorhandler(500)
def server_error(e):
    err_desc = getattr(e, 'description', str(e))
    return render_template("setup.html", error=f"500 Internal Server Error: {err_desc}"), 500

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5001))
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    app.run(debug=debug_mode, port=port)