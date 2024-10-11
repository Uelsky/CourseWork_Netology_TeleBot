import json


def create_db(cur):

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS english(
            id SERIAL PRIMARY KEY,
            word VARCHAR(30) NOT NULL,
            id_user VARCHAR(30) NOT NULL
            );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS russian(
            id SERIAL PRIMARY KEY,
            word VARCHAR(30) NOT NULL,
            id_eng INTEGER REFERENCES english(id)
            );
        """
    )


def new_user(cur, cid):

    with open(r"./fixtures/test_data.json", encoding='utf-8') as file:
        words = json.load(file)
        for word in words:
            cur.execute(
                """
                INSERT INTO english (word, id_user)
                VALUES(%s, %s)
                RETURNING id;
                """, (word, str(cid))
            )
            eng_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO russian (word, id_eng)
                VALUES(%s, %s);
                """, (words[word], eng_id)
            )


def search_words(cur, cid):
    cur.execute(
        """
        SELECT r.word, e.word
        FROM russian r
        JOIN english e ON e.id = r.id_eng
        WHERE e.id_user = %s;
        """, (str(cid),)
    )
    return cur.fetchall()


def adding_word(cur, cid):
    with open(r"./fixtures/test_data.json", encoding='utf-8') as file:
        words = json.load(file)
        eng_words = [i for i in words]
        cur.execute(
            """
            SELECT r.word, e.word
            FROM russian r
            JOIN english e ON e.id = r.id_eng
            WHERE e.word NOT IN %s;
            """, (eng_words,)
        )
        words_for_add = cur.fetchone()

        cur.execute(
            """
            INSERT INTO english (word, id_user)
            VALUES(%s, %s)
            RETURNING id;
            """, (words_for_add[1], str(cid))
        )
        eng_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO russian (word, id_eng)
            VALUES(%s, %s);
            """, (words_for_add[0], eng_id)
        )


def del_word(cur, en_word, cid):
    cur.execute(
        """
        SELECT r.word, r.id_eng
        FROM russian r
        JOIN english e ON e.id = r.id_eng
        WHERE e.word = %s;
        """, (en_word,)
    )
    ans = cur.fetchone()
    ru_word = ans[0][0]
    en_id = ans[0][1]

    cur.execute(
        """
        DELETE FROM english
        WHERE word = %s 
        AND id_user = %s;
        """, (en_word, str(cid))
    )

    cur.execute(
        """
        DELETE FROM russian
        WHERE word = %s
        AND id_eng = %s
        """, (ru_word, en_id)
    )
