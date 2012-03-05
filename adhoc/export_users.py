from sqlite3 import dbapi2 as sqlite
import csv
import optparse


def main():
    p = optparse.OptionParser(usage='%prog [options] path/to/chirp.db')    
    (options, args) = p.parse_args()
    if len(args) != 1:
        p.error('incorrect args')
    chirp_db = args[0]    
    connection = sqlite.connect(chirp_db)
    
    cursor = connection.cursor()
    cursor.execute("select * from auth_user where is_active=1")
    users = cursor.fetchall()
    
    users_file = open('users.csv', 'w')
    writer = csv.writer(users_file)
    fields = [d[0] for d in cursor.description]
    for user in users:
        data = dict(zip(fields, user))
        if not data['email']:
            raise ValueError('active DJs cannot have empty emails: %s' % data)
        writer.writerow([data['email'], data['first_name'], data['last_name'],
                        # empty password so that reset is forced after import:
                        '', data['is_active'], data['is_superuser'],
                        data['date_joined'].split('.')[0], 'dj'])
    
    cursor.close()
    connection.close()
    print "Wrote %s" % users_file.name
    users_file.close()
    
if __name__ == '__main__':
    main()    
    
    

