from model.utils import TableToGenerate, my_sql


def __drop_all_tables():
    # NOT BIND
    tables = TableToGenerate.show_tables_request()
    print(type(tables))
    for table in tables:
        print(type(table), table)

    format_param = ", ".join([t for t in tables])

    query = "DROP TABLES {}".format(format_param)
    print(query)

    my_sql.execute_and_close(query=query)


if __name__ == '__main__':
    __drop_all_tables()
