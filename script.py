import sqlite3
import sys, os
import datetime
import getpass
import uuid


conn = None
cursor = None

'''
Purpose: Connects script to database
Inputs:
    path: File path of where database is store
Returns:
    None
'''
def connect(path):
    global conn, cursor
    
    # connect
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON;')
    conn.commit()
    return


'''
Purpose: Displays message asking if user is customer or editor
Inputs:
    None
Returns:
    None
'''
def define_user():
    # Display message
    print("-"*20)
    print("Please press 1 if you are a customer")
    print("Please press 2 if you are an editor")
    print("Press 'q' to quit")
    print("-"*20)


'''
Purpose: Displays main menu prompt
Inputs:
    None
Returns:
    None
'''
def main_prompt():

    # stuff that gets displayed on menu
    print("-"*20)
    print("Please press 1 for customer log in")
    print("If you do not have an account, press 2 to register")
    print("Press 'q' to quit")
    print("-"*20)
    
'''
Purpose: Registers a customer
Inputs:
    None
Returns:
    None
'''
def register_customer():
    
    global conn,cursor
    
    # Ask for user input
    valid_input = False
    while not valid_input:
        cid = input("Enter a 4 digit id: ")
        name = input("Enter your name: ")
        pwd = getpass.getpass("Password: ")
        
        # Check if cid is longer than 4 digits
        if len(cid) > 4:
            print("id cannot be longer than 4 digits\n")
        
        else:
            # Check if cid already exists
            cursor.execute("SELECT cid FROM customers WHERE cid=?", (cid,))
            if cursor.fetchone() == None:
                    valid_input = True
            else:
                print("Error, cid already exists.\n")
        
    # insert
    cursor.execute("INSERT INTO customers(cid,name,pwd) VALUES(?,?,?);", (cid,name,pwd))
    conn.commit()

    print("Your account has been created. \n")

'''
Purpose: Customer login
Inputs:
    cid: Integer representing cid of customer
    pwd: Password of customer
Returns:
    Boolean: True if login was successful. False if otherwise
'''
def login(cid,pwd):

    global conn, cursor
    
    # Check if customer is in database
    cursor.execute("SELECT * FROM customers WHERE cid = ? AND pwd = ?;",(cid,pwd))
    row = cursor.fetchone()
    
    # print feedback message
    print('\n')
    if row:
        print("Hello there, " + row[1] + "!")
        return True
    else:
        print("Invalid username or password")
        return False

'''
Purpose: Editor login
Inputs:
    eid: Integer representing eid of editor
    pwd: password of editor
Returns:
    Boolean: True if login was successfull. False otherwise.
'''
def login_editor(eid,pwd):
    global conn, cursor
    
    # check if customer is in database
    cursor.execute("SELECT * FROM editors WHERE eid = ? AND pwd = ?;",(eid,pwd))
    row = cursor.fetchone()
    
    # print feedback message
    print('\n')
    if row:
        print("Hello there, " + row[0] + "!")
        return True
    else:
        print("Invalid username or password")
        return False

'''
Purpose: Allows a customer to start a session at the current date.
Inputs:
    cid: Integer representing cid of customer
Returns:
    sid: Integer representing session id
'''
def start_session(cid):
    global conn, cursor

    sid = str(uuid.uuid4())   # unique session id
    sdate = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')   # set start date
    duration = None
    
    # Input session into table
    cursor.execute("INSERT INTO sessions VALUES(?,?,?, ?);", (sid,cid,sdate, duration))
    conn.commit()
    print("Session created.")
    
    
    return sid

'''
Purpose: Allows customer to search for movie using keywords. Customer can then
select movie to see more information including cast member and number of customers
who have watched it. Customer can then choose to follow cast member or start watching movie
Inputs:
    cid: Integer representing cid of customer
    sid: Integer representing session id
Returns:
    None: if no movie started being watched OR
    the start time and mid of movie if movie was started
    
'''
def search_movies(cid,sid):
    global conn, cursor
    
    # Ask user for keywords and find movies with keywords
    search = input("Search a movie: ")
    search = "%" + search + "%"
    cursor.execute('''select title, year, runtime 
                        from movies 
                        where title like ?
                        union
                        select distinct title, year, runtime
                        from movies, casts
                        where movies.mid = casts.mid and role like ?
                        union
                        select title, year, runtime
                        from movies, casts, moviePeople
                        where movies.mid = casts.mid and casts.pid = moviePeople.pid 
                        and name like ?;
                        ''', (search,search,search))
    movie_results = cursor.fetchall()
    print("\nResults found: ")
    choice = show_results(movie_results)
    
    # If user chooses to exit
    if choice == 'e':
        return None, None
    can_follow = False
    mid = None
    
    # If no search results found
    if(len(movie_results) == 0):
        print("None.")
        return None, None
        
    try:
        result = show_cast_and_watch_count(movie_results, choice)   # names of casts in movie
        if len(result) > 0:
            can_follow = True
            print("Select one of these casts to follow them or press e to leave")
            cursor.execute('''select movies.mid 
                        from watch, movies 
                        where movies.mid = watch.mid and title = ?;''', (movie_results[choice - 1][0],))
            mid = cursor.fetchone()[0]

        print("Press 's' to start watching this movie")
        print("Press 'e' to exit")
        choice2 = input()
        wants_to_follow = False

        # if customer wants to follow
        if choice2.isnumeric() and 1 <= int(choice2) and int(choice2) <= len(result) and can_follow:
            wants_to_follow = True
            
        while not wants_to_follow:
            if choice2 == 'e':   # exit
                return None, None
            
            # start watching movie
            if choice2 == "s":
                watch_movie(sid,cid,mid)
                t_rec = datetime.datetime.now()
                print("starting time is: ", t_rec)
                return t_rec, mid   # return start time and mid
            
            
            if choice2.isnumeric() and 1 <= int(choice2) and int(choice2) <= len(result) and can_follow:
                wants_to_follow = True
            else:
                choice2 = input("Please enter a valid input: ")
                
        follow_person(cid, result,choice2)   # follow
    
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        pass

'''
Purpose: Allows customer to watch a movie
Inputs:
    cid: Integer representing cid of customer
    sid: Integer representing sid of session
    mid: Integer representing mid of movie
Returns: None
'''
def watch_movie(sid,cid,mid):
    # insert into watch table
    if sid != None:
        cursor.execute("insert into watch values(?,?,?,?);", (sid,cid,mid,0))
        conn.commit()
        print("Watching movie..")
        return 
    else:
        print("You havent started a session yet")
        return 
'''
Purpose: Displays casts of movie and its watch count
Inputs:
    movie_results: List of movies
    choice: Index corresponding the movie the user wants to explore
Returns:
    result: Names of casts in the movie
'''
def show_cast_and_watch_count(movie_results, choice):

    print(movie_results[choice - 1][0] + "\n")  # movie selected
    
    # Get the name of casts
    print("Cast: ")
    cursor.execute('''select name from casts, moviePeople, movies 
    where casts.pid = moviePeople.pid and movies.mid = casts.mid and title = ?;''', (movie_results[choice - 1][0],))
    result = cursor.fetchall()
    
    # Print each cast member
    try:
        index = 1
        for each in result:
            print(str(index) + ".) " + each[0])
            index += 1
    except Exception:
        print("No results found\n")
        pass
    
    # Find number of people who have watched movie
    cursor.execute('''select movies.mid 
                    from watch, movies 
                    where movies.mid = watch.mid and title = ?;''', (movie_results[choice - 1][0],))
    cursor.execute('''select count (distinct cid) 
                    from watch, movies 
                    where movies.mid = watch.mid and title = ? and duration >= runtime * 0.5;'''
                    , (movie_results[choice - 1][0],))
    watch_num = cursor.fetchone()
    print("\n" +str(watch_num[0]) + " people have watched this movie.")
    
    return result
'''
Purpose: Allows a person to follow a cast member
Inputs:
    cid: Integer representing cid of customer
    result: Name of cast
    choice2: Index corresponding the person the customer wants to follow
Returns:
    None
'''
def follow_person(cid,result, choice2):
    
    choice2 = int(choice2)
    
    try:
        # follow person
        cursor.execute('''select distinct casts.pid 
        from casts, moviePeople 
        where moviePeople.pid = casts.pid and name = ? ''',(result[choice2 - 1]))
        pid = cursor.fetchone()
        cursor.execute("insert into follows values(?,?);", (cid,pid[0]))
        print("You now follow that person!")
        conn.commit()

    except Exception:
        print("You already follow that person")

'''
Purpose: Shows results of movies every on 5th movie
Inputs:
    movie_list: List of movies to be displayed
Returns:
    choice: Integer that represents the user's choice
'''
def show_results(movie_list):

    index = 1
    j = 0 # j is a counter that traverses every 5 movies
    end_of_results = False
    
    # Show movies 5 at a time
    while index <= len(movie_list) and not end_of_results:
        while j < index + 4:
            print(str(j + 1) + ".) " + movie_list[j][0] + ' ' +  str(movie_list[j][1]) + ' ' + str(movie_list[j][2]) + '\n')
            j += 1
            if j == len(movie_list):
                end_of_results = True
                break
        index += 5
        
        # Ask user what they would like to do
        print("Select one of these movies to see more information.")
        if not end_of_results:
            print("Press m to browse through more movies")
        choice = input("Or press e to leave: ")        
        valid_input = False
        
        # Check for valid input and return
        while not valid_input:
            if choice == 'm' and not end_of_results:
                break
            elif choice == 'e':
                return 'e'
            elif choice.isnumeric() and 1 <= int(choice) and int(choice) <= index - 1:
                print("You chose " + choice)
                return int(choice)
            else:
                choice = input("Please enter a valid input: ")

'''
Purpose: End watching a movie and set the duration
    cid: Integer representing cid of customer
    sid: Integer representing sid of session
    mid: Integer representing mid of movie
    movie_start_time:
        if movie is being watched: type datetime.datetime representing the date and time a movie was started
        if movie is not being watched: None
Returns: None
'''
def end_watching_movie(cid, sid, mid ,movie_start_time):
    global conn, cursor
    
    # Check if customer is watching movie
    if mid != None:
    
        # Get the duration of the movie
        cursor.execute( '''
                        SELECT runtime
                        FROM movies
                        WHERE mid =?;
                        ''', (mid,))
        movie_duration = cursor.fetchone()[0]
        
        # Find how long customer has been watching movie
        current_datetime = datetime.datetime.now()
        movie_watched_time = ((current_datetime - movie_start_time).total_seconds())/60
        
        # Update watch if customer has watched more than half of the movie
        if movie_watched_time >= 0.5 * movie_duration:
            
            # check if duration watched exceeds movie
            if movie_watched_time > movie_duration:
                movie_watched_time = movie_duration
                
            cursor.execute( '''
                            INSERT INTO watch(sid, cid, mid, duration) VALUES
                            (:sid, :cid, :mid, :duration);
                            ''', {"duration":movie_watched_time, "cid":cid, "sid":sid, "mid":mid})
            
    conn.commit()
    print("Movie successfully ended")
    return


'''
Purpose: Ends the current session. If a customer is watching a movie, those will end as well.
Inputs:
    cid: Integer representing cid of customer
    sid: Integer representing sid of session
    mid: Integer representing mid of movie
    movie_start_time:
        if movie is being watched: type datetime.datetime representing the date and time a movie was started
        if movie is not being watched: None
Returns: None
'''
def end_session(cid, sid, mid, movie_start_time):
    global conn, cursor
    
    # Get the start time of the session
    cursor.execute( '''
                    SELECT sdate
                    FROM sessions
                    WHERE sid =? AND cid =?;
                    ''', (sid, cid))
    start_time = cursor.fetchone()
    
    # Update duration of session
    cursor.execute( '''
                    UPDATE sessions
                    SET duration =  ROUND((JULIANDAY((strftime('%Y-%m-%d %H:%M:%S', datetime('now', 'localtime')))) - JULIANDAY(?)) * 1440)
                    WHERE cid=? AND sid=?;
                    ''', (start_time[0], cid, sid))
    
    # Check if customer is watching movie
    if mid != None:
        end_watching_movie(cid, sid, mid ,movie_start_time)

    conn.commit()
    return
        
'''
Purpose: Allows editor to add a movie
Inputs:
    None
Returns:
    None
'''
def add_movie():
    global conn, cursor
    
    # Ask for movie information
    mid = input("Enter a movie id: ")
    title = input("Enter the title: ")
    year = input("Enter the year: ")
    runtime = input("Enter the runtime: ")
    
    # insert movie into database
    cursor.execute("INSERT INTO movies(mid,title,year,runtime) VALUES(?,?,?,?);", (mid,title,year,runtime))
    conn.commit()

    # ask for id of cast member
    pid = input("Enter the id of the cast member: ")
    cursor.execute("SELECT mp.name, mp.birthYear FROM moviePeople mp WHERE pid = ?;",(pid,))
    row = cursor.fetchone()

    # display name and birth year
    print('\n')
    if row:
        print("This cast member's name is: " + row[0])
        print("This cast member's birth year is: ", row[1])

        # ask the editor to confirm or reject this cast member
        confirm_role = input("Enter 1 to confirm this cast member, enter 2 to reject"
            " this cast member: ")

        # provide role if confirmed
        if confirm_role == "1":
            role = input("Enter the cast member role: ")
            cursor.execute("INSERT INTO casts VALUES(?,?,?);", (mid,pid,role))
            conn.commit()

        # cast member being rejected
        elif confirm_role == "2":
            print("cast member " + row[0] + " rejected")
            cursor.execute("DELETE FROM casts WHERE pid = ?;", (pid,))
            cursor.execute("DELETE FROM follows WHERE pid = ?;", (pid,))
            cursor.execute("DELETE FROM moviePeople WHERE pid = ?;", (pid,))

            conn.commit()

    # cast member does not exist, add the member
    else:
        print("This cast member does not exist! Please add the member now")
        pid = input("Enter the id of the cast member: ")
        name = input("Enter the name of the cast member: ")
        birthYear = input("Enter the birth year of the cast member: ")
        cursor.execute("INSERT INTO moviePeople(pid,name,birthYear) VALUES(?,?,?);", (pid,name,birthYear))
        conn.commit()
        print("Cast member" + ": " + name + " " + "added!")


'''
Purpose: Allows editor to insert, update, or delete a recommendation
Inputs:
    None
Returns:
    None
'''
def update_a_recommendation():
    global conn, cursor
    
    # Ask editor for range until valid input provided
    not_valid_choice = True
    while not_valid_choice:
        choice = input("1.Monthly \n2.Annual \n3.All Time \n4.Quit\nSelect 1,2,3 for range or 4 to quit: ")
        if choice[0] == "1":
            time_frame = '-30 day'
            not_valid_choice = False
        elif choice[0] == "2":
            time_frame = '-365 day'
            not_valid_choice = False
        elif choice[0] == "3":
            time_frame = '-999 year'
            not_valid_choice = False
        elif choice[0] == "4":
            return
    
    # Find movie pairs that customers have watched
    cursor.execute( '''
                    SELECT m1.title, m2.title, COUNT(*), m1.mid, m2.mid
                    FROM watch w1, watch w2, movies m1, movies m2, sessions s1, sessions s2
                    WHERE w1.mid != w2.mid
                    AND w1.cid = w2.cid
                    AND w1.mid = m1.mid
                    AND w2.mid = m2.mid
                    AND w1.sid = s1.sid AND w1.cid = s1.cid
                    AND w2.sid = s2.sid AND w2.cid = s2.cid
                    AND s1.sdate > date('now', ?)
                    AND s2.sdate > date('now', ?)
                    GROUP BY w1.mid, m1.title, w2.mid, m2.title
                    ORDER BY COUNT(*) DESC;
                    ''', (time_frame,time_frame))
    movie_pairs = cursor.fetchall()
    
    print("\n%-10s%-26s%-26s%-20s%-5s" % ("Pair", "Movie 1", "Movie 2", "# of Customers", "Score"))
    option_num = 0
    
    # Find if pair is in recommended
    for pair in movie_pairs:
        movie1_id = pair[3]
        movie2_id = pair[4]
        cursor.execute( '''SELECT score
                        FROM recommendations
                        WHERE watched=?
                        AND recommended=?;
                        ''', (movie1_id, movie2_id))
        score = cursor.fetchone()
        if score is not None:
            score = score[0]
        print("%-10s%-26s%-26s%-20d%-5s" % (option_num, pair[0], pair[1], pair[2], score))
        option_num += 1
                    
    # Ask editor to select pair
    valid_input = False
    while not valid_input:
        pair = input("\nPlease select a pair: ")
        try:
            pair = int(pair)
            if pair < option_num:
                valid_input=True
        except ValueError:
                    pass
                    
    movie1_mid = movie_pairs[pair][3]
    movie2_mid = movie_pairs[pair][4]
    
    # Check if movie is in recommended
    cursor.execute( '''SELECT score
                    FROM recommendations
                    WHERE watched=?
                    AND recommended=?;
                    ''', (movie1_mid, movie2_mid))
    score = cursor.fetchone()
    
    # Ask editor to select option
    valid_selection = False
    while not valid_selection:
        selection = input("\nOptions: \n1. Add to recommended \n2. Delete from recommended \n3. Update score\n4. Quit\nSelect what you would like to do: ")
        
        
        # Ask for score
        if selection == "1" or selection == "3":
            valid_score= False
            while not valid_score:
                new_score = input("Please enter score: ")
                try:
                    new_score = float(new_score)
                    valid_score = True
                except ValueError:
                    pass
        
            # Check if pair is already in recommendations and insert if not
            if selection == "1":
                if score is not None:
                    print("Error: Movie pair is already in recommendations.")
                else:
                    cursor.execute( ''' INSERT INTO recommendations(watched,recommended,score)
                                    VALUES(?,?,?);''', (movie1_mid, movie2_mid, new_score))
                    print("Movies successfully added to recommendations!")
                    valid_selection = True
                                    
            # Update score
            else:
                cursor.execute( ''' UPDATE recommendations
                                SET score=?
                                WHERE watched=?
                                AND recommended=?;''', (new_score, movie1_mid, movie2_mid))
                print("Score successfully updated!")
                valid_selection = True
                
        # Delete movie from recommendations if movie is in recommendations table
        elif selection == "2":
            
            if score is None:
                print("Error: Movie pair is not in recommendations and cannot be deleted.")
            else:
                cursor.execute( ''' DELETE FROM recommendations
                                    WHERE watched=? AND recommended=?;''', (movie1_mid, movie2_mid))
                print("Movies successfully deleted from recommendations!")
                valid_selection = True
        
        if selection == "4":
            return
            
    conn.commit()
    return

'''
    Purpose:  Prompts customer some choices to pick
    Inputs:
        cid: Integer representing cid of customer
    Returns: True (if user wants to log out.)
             False (if user wants to quit application.)
'''
def customer_prompt(cid):
    sid = None
    mid1 = None
    movie_start_time = None
    logged_out = False
    
    # Ask user what to do
    while not logged_out:
        print("-"*20)
        print("What would you like to do?")

        # print options
        options = ["1.) Start a session", "2.) Search for movies", "3.) End watching a movie", "4.) End a session"
        , "5.) Log out ", "6.) Quit application"]
        for each in options:
            print(each)
        
        choice = input("\nSelect a number of your choice: ")

        # start session
        if choice == "1":
            sid = start_session(cid)
        
        # search for movies
        elif choice == "2":
            if sid == None:
                print("Start a session first!")
            else:
                movie_start_time, mid1 = search_movies(cid,sid)
                if movie_start_time == None:
                    pass
        
        # end watching movie
        elif choice == "3":
            if mid1 is not None:
                end_watching_movie(cid, sid, mid1, movie_start_time)
            else:
                print("No movie to end")
                
        # end session
        elif choice == "4":
            if sid is not None:
                end_session(cid, sid, mid1, movie_start_time)
            else:
                print("No session to end\n")
                
        # Logout
        elif choice == "5":
            return True
            
        # Exit app
        elif choice == "6":
            return False
        else:
            print("Invalid input!")


def editor_prompt():
    while True:
        print("-"*20)
        print("What would you like to do?")

        options = ["1.) Add a movie", "2.) Update a recommendation", "3.) Log out ", "4.) Quit application"]
        
        for each in options:
            print(each)
        
        choice = input("\nSelect a number of your choice: ")

        if choice == "1":
            add_movie()
        elif choice == "2":
            update_a_recommendation()
        elif choice == "3": # return True to log out
            return True
        elif choice == "4": # return False to exit app
            return False
        else:
            print("Invalid input!")


def main():
    global conn, cursor
    
    path_not_valid = True
    
    # Ask for valid path
    while path_not_valid:
        try:
            path = input("Enter a path for db: ")
            connect(path)
            path_not_valid = False
        except:
            print("Path not valid.")
    
    logged_in = False

    while not logged_in:
        define_user()
        
        # Ask user to quit, login, or register.
        user_type = input()
        if user_type.lower() == 'q':  # quit
            break
       
        elif user_type == '1':   # customer
            main_prompt()
            option = input()

            if option.lower() == 'q':    # quit
                break
                
            # customer login
            elif option == '1':
                cid = input("Enter your cid: ")
                pwd = getpass.getpass("Password: ")
                if login(cid,pwd): # if returns true, log in was succesful. false if otherwise
                    logged_in = True
                    
            # register customer
            elif option == '2':
                register_customer()
                    
            if logged_in:
                if (customer_prompt(cid)): # if this returns true then the user logged out
                    logged_in = False
                else:                   # if its false the user wants to exit app
                    break

        elif user_type == '2':
            eid = input("Enter an id: ")
            pwd = getpass.getpass("Password: ")

            if login_editor(eid,pwd):
                logged_in = True

            if logged_in:
                if (editor_prompt()):   # if this returns true then the user logged out
                    logged_in = False
                else:                   # if its false the user wants to exit app
                    break
    



if __name__ == "__main__":
    main()
