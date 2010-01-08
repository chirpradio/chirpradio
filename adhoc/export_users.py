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
    
    ## sqlite
    #0:id,1:username,2:first_name,3:last_name
    #4:email,5:password,6:is_staff,7:is_active,8:is_superuser
    #9:last_login,10:date_joined
     
    ## To model:
    #    email:4,first_name:2,last_name:3,password,is_active:7,is_superuser:8
    #    last_login:9 (ignored) ,date_joined:10,roles
    
    users_file = open('users.csv', 'w')
    writer = csv.writer(users_file)
    for user in users:
        email = user[4]
        # empty password so that reset is forced after import:
        writer.writerow([email,user[2],user[3], '', user[7],user[8],user[10].split('.')[0], 'dj'])
    
    cursor.close()
    connection.close()
    print "Wrote %s" % users_file.name
    users_file.close()
    
if __name__ == '__main__':
    main()    
    
    

