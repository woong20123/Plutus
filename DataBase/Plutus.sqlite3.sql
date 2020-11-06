BEGIN TRANSACTION;
DROP TABLE IF EXISTS "target_stock_info";
CREATE TABLE IF NOT EXISTS "target_stock_info" (
	"name"	TEXT NOT NULL,
	"sell_target_price"	INTEGER NOT NULL,
	"buy_target_price"	INTEGER NOT NULL,
	"stock_type"	TEXT,
	"current_price"	INTEGER NOT NULL,
	"invest_grade"	TEXT,
	PRIMARY KEY("name")
);
DROP TABLE IF EXISTS "stock_info";
CREATE TABLE IF NOT EXISTS "stock_info" (
	"code"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("name")
);
DROP TABLE IF EXISTS "have_stock_info";
CREATE TABLE IF NOT EXISTS "have_stock_info" (
	"code"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	"buy_total_price"	INTEGER NOT NULL,
	"cur_price"	INTEGER NOT NULL,
	"have_count"	INTEGER NOT NULL,
	PRIMARY KEY("name")
);
DROP TABLE IF EXISTS "purchase_per_stock";
CREATE TABLE IF NOT EXISTS "purchase_per_stock" (
	"type"	TEXT NOT NULL,
	"purchase"	INTEGER NOT NULL,
	PRIMARY KEY("type")
);
COMMIT;
