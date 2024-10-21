import json


def create_db(cur):
    """
    Функция create_db создает пять таблиц в базе данных:
    words содержит аyглийские слова;
    translates содержит переводы;
    deleted_words содержит список идентификатов удаленных слов пользователем;
    word_rating содержит рейтинг усваеваемости слова пользователем;
    user_statistic содержит количество правильных ответов пользователя.
    """

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS words(
            id SERIAL PRIMARY KEY,
            word VARCHAR(30) NOT NULL,
            id_user VARCHAR(30) NOT NULL
            );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS translates(
            id SERIAL PRIMARY KEY,
            word VARCHAR(30) NOT NULL,
            id_eng INTEGER REFERENCES words(id)
            );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS deleted_words(
            id SERIAL PRIMARY KEY,
            id_eng INTEGER REFERENCES words(id),
            id_transl INTEGER REFERENCES translates(id),
            id_user VARCHAR(30) NOT NULL
            );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS word_rating(
            id SERIAL PRIMARY KEY,
            id_user VARCHAR(30),
            id_eng INTEGER REFERENCES words(id),
            id_transl INTEGER REFERENCES translates(id),
            rating INTEGER NOT NULL
            );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_statistic(
            id SERIAL PRIMARY KEY,
            id_user VARCHAR(30) NOT NULL,
            stat INTEGER NOT NULL
            );
        """
    )


def new_user(cur, cid):
    """
    Функция new_user заполняет таблицы БД базовыми английскими словами и переводами
    из файла fixtures/test_data.json для нового пользователя,строит зависимости между
    таблицами по индивидуальному индентификатору пользователя,настраивает статискику и
    рейтинги усваиваемости слов.
    """

    with open(r"./fixtures/test_data.json", encoding='utf-8') as file:
        words = json.load(file)
        for word in words:
            cur.execute(
                """
                INSERT INTO words (word, id_user)
                VALUES(%s, %s)
                RETURNING id;
                """, (word, str(cid))
            )
            eng_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO translates (word, id_eng)
                VALUES(%s, %s)
                RETURNING id;
                """, (words[word], eng_id)
            )
            transl_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO word_rating (id_user, id_eng, id_transl, rating)
                VALUES(%s, %s, %s, %s);
                """, (str(cid) ,eng_id, transl_id, 0)
            )

            cur.execute(
                """
                INSERT INTO user_statistic (id_user, stat)
                VALUES(%s, %s)
                """, (str(cid), 0)
            )


def search_words(cur, cid):
    """
    Функция search_words выбирает из базы данных список слов для изучения и их переводы,
    сравнивает первичный результат с наличием слов и переводов в таблице удаленных слов,
    делает выборку для конечного вывода в пользовательский интерфейс.
    """

    cur.execute(
        """
        SELECT t.word, w.word
        FROM translates t
        JOIN words w ON w.id = t.id_eng
        WHERE w.id_user = %s;
        """, (str(cid),)
    )
    all_words = cur.fetchall()

    deleted_words = []
    try:
        cur.execute(
            """
            SELECT w.word, t.word
            FROM deleted_words dw
            JOIN words w ON w.id = dw.id_eng
            JOIN translates t ON t.id_eng = w.id
            WHERE w.id_user = %s;
            """, (str(cid),)
        )
        deleted_words += cur.fetchall()
    except:
        pass

    result = []
    en_list = []
    transl_list = []
    if len(deleted_words) > 0:
        en_list += [i[0] for i in deleted_words]
        transl_list += [i[1] for i in deleted_words]
    for i in all_words:
        if i[1] not in en_list and i[0] not in transl_list:
            result.append(i)

    return result


def true_answer(cur, cid, en_word, translate):
    """
    Функция true_answer вызывается при правильном ответе пользователя при выборе перевода.
    Функция обновляет рейтинг усваивемости слова, а также общую статискику правильных
    ответов пользователя.
    """

    cur.execute(
        """
        SELECT t.id, w.id
        FROM translates t
        JOIN words w ON w.id = t.id_eng
        WHERE w.word = %s
        AND t.word = %s
        AND w.id_user = %s;
        """, (en_word, translate, str(cid))
    )
    ans = cur.fetchone()
    transl_id = ans[0][0]
    en_id = ans[0][1]

    cur.execute(
        """
        UPDATE word_rating
        SET rating = rating + 1
        WHERE id_user = %s, id_eng = %s, id_transl = %s;
        """, (str(cid), en_id, transl_id)
    )

    cur.execute(
        """
        SELECT rating
        FROM word_rating
        WHERE id_user = %s, id_eng = %s, id_transl = %s;
        """, (str(cid), en_id, transl_id)
    )
    ans = cur.fetchone()[0]

    if int(ans) == 20:
        del_word(cur, cid, en_word, translate)

    cur.execute(
        """
        UPDATE user_statistic
        SET stat = stat + 1
        WHERE id_user = %s;
        """, (str(cid),)
    )


def adding_word(cur, cid, en_word, translate):
    """
    Функция adding_word вызывается пользователем при нажатии кнопки "добавить слово".
    Функция индивидуально добавляет в БД пользовательские значения английского слова
    и его перевода.
    """

    cur.execute(
        """
        INSERT INTO words (word, id_user)
        VALUES(%s, %s)
        RETURNING id;
        """, (en_word, str(cid))
    )
    eng_id = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO translates (word, id_eng)
        VALUES(%s, %s)
        RETURNING id;
        """, (translate, eng_id)
    )
    transl_id = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO word_rating (id_eng, id_transl, rating)
        VALUES(%s, %s, %s);
        """, (eng_id, transl_id, 0)
    )


def del_word(cur, cid, en_word, translate):
    """
    Функция del_word вызывается пользователем при нажатии кнопки "удалить слово".
    Функция индивидуально удаляет из БД значения английского слова и его перевода.
    """

    cur.execute(
        """
        SELECT t.id, w.id
        FROM translates t
        JOIN words w ON w.id = t.id_eng
        WHERE w.word = %s
        AND t.word = %s
        AND w.id_user = %s;
        """, (en_word, translate, str(cid))
    )
    ans = cur.fetchone()
    transl_id = ans[0][0]
    en_id = ans[0][1]

    cur.execute(
        """
        INSERT INTO deleted_words (id_eng, id_transl, id_user)
        VALUES(%s, %s, %s);
        """, (en_id, transl_id, str(cid))
    )

