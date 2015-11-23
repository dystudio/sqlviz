import website.sql_manager as sql_manager
import website.models
import models

class Crawler():
    def __init__(self, request):
        self.request = request
        pass

    def crawl_all(self):
        """
        Find all databases in website and run crawl_database on then
        """
        con_list = website.models.Db.objects.all()
        print con_list
        for con_id in con_list:
            self.crawl_con(con_id)

    def crawl_con(self, con_id):
        con = website.models.Db.objects.filter(id=con_id.id).first()

        # Switch in database Type
        if con.type == 'MySQL':
            self.dmm = sql_manager.MySQLManager(con, self.request)
        elif con.type == 'Postgres':
            self.dmm = sql_manager.PSQLManager(con, self.request)

        self.dmm.find_database()
        self.dmm.run_query()
        db_array = self.dmm.RQ.data_array[1]
        print db_array
        for db_id in db_array:
            self.crawl_database(con_id, db_id)

    def crawl_database(self, con_id, db_id):
        self.dmm.show_tables(db_id)
        self.dmm.run_query()
        table_array = [i[0] for i in self.dmm.RQ.data_array]
        table_array.pop(0)
        for table_id in table_array:
            obj, created = models.Table.objects.update_or_create(
                db = con_id,
                database_name = db_id,
                title = table_id,
                #description = 'Autogenerated by SQLViz'
                )
            self.crawl_table(db_id, table_id, obj)

    def crawl_table(self, db_id, table_id, table_obj):
        self.dmm.describe_table(db_id, table_id)
        self.dmm.run_query()
        column_array = self.dmm.normalize_table_describe()
        column_array.pop(0)
        #print column_array
        for col in column_array:
            #print 'cols,' , col
            #print obj, ':' , qtype(obj)
            obj, created = models.Column.objects.update_or_create(
                table = table_obj,
                name = col[0],
                type = col[1],
                mean=0,
                min=0,
                max=0,
                mode=0
                )