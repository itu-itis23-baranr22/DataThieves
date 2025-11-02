import mysql.connector


connection = mysql.connector.connect(
        host='#',
        user='#',
        password='#',
        database='#'       
    )

cursor = connection.cursor()


cursor.execute("""
        SET FOREIGN_KEY_CHECKS = 0;
        DROP TABLE IF EXISTS badges, comments, postHistory, postLinks, posts, tags, users, votes;
        SET FOREIGN_KEY_CHECKS = 1;
        """)


cursor.execute("""
        CREATE TABLE users (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            Reputation INT,
            CreationDate DATETIME,
            DisplayName VARCHAR(255),
            LastAccessDate DATETIME,
            WebsiteUrl VARCHAR(255),
            Location VARCHAR(255),
            AboutMe TEXT,
            Views INT,
            UpVotes INT,
            DownVotes INT,
            AccountId INT,
            Age INT,
            ProfileImageUrl VARCHAR(500)
        );
        """)

cursor.execute("""
        CREATE TABLE posts (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            PostTypeId INT,
            AcceptedAnswerId INT,
            CreationDate DATETIME,
            Score INT,
            ViewCount INT,
            Body TEXT,
            OwnerUserId INT,
            LastActivityDate DATETIME,
            Title VARCHAR(500),
            Tags VARCHAR(500),
            AnswerCount INT,
            CommentCount INT,
            FavoriteCount INT,
            LastEditorUserId INT,
            LastEditDate DATETIME,
            CommunityOwnedDate DATETIME,
            ParentId INT,
            ClosedDate DATETIME,
            OwnerDisplayName VARCHAR(255),
            LastEditorDisplayName VARCHAR(255),
            FOREIGN KEY (OwnerUserId) REFERENCES users(Id),
            FOREIGN KEY (ParentId) REFERENCES posts(Id)
        );
        """)

cursor.execute("""
        CREATE TABLE comments (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            PostId INT,
            Score INT,
            Text TEXT,
            CreationDate DATETIME,
            UserId INT,
            UserDisplayName VARCHAR(255),
            FOREIGN KEY (PostId) REFERENCES posts(Id),
            FOREIGN KEY (UserId) REFERENCES users(Id)
        );
        """)

cursor.execute("""
        CREATE TABLE postHistory (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            PostHistoryTypeId INT,
            PostId INT,
            RevisionGUID VARCHAR(255),
            CreationDate DATETIME,
            UserId INT,
            Text TEXT,
            Comment TEXT,
            UserDisplayName VARCHAR(255),
            FOREIGN KEY (PostId) REFERENCES posts(Id),
            FOREIGN KEY (UserId) REFERENCES users(Id)
        );
        """)

cursor.execute("""
        CREATE TABLE postLinks (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            CreationDate DATETIME,
            PostId INT,
            RelatedPostId INT,
            LinkTypeId INT,
            FOREIGN KEY (PostId) REFERENCES posts(Id),
            FOREIGN KEY (RelatedPostId) REFERENCES posts(Id)
        );
        """)

cursor.execute("""
        CREATE TABLE tags (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            TagName VARCHAR(100),
            Count INT,
            ExcerptPostId INT,
            WikiPostId INT,
            FOREIGN KEY (ExcerptPostId) REFERENCES posts(Id),
            FOREIGN KEY (WikiPostId) REFERENCES posts(Id)
        );
        """)

cursor.execute("""
        CREATE TABLE badges (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            UserId INT,
            Name VARCHAR(255),
            Date DATETIME,
            FOREIGN KEY (UserId) REFERENCES users(Id)
        );
        """)

cursor.execute("""
        CREATE TABLE votes (
            Id INT PRIMARY KEY AUTO_INCREMENT,
            PostId INT,
            VoteTypeId INT,
            CreationDate DATETIME,
            UserId INT,
            BountyAmount INT,
            FOREIGN KEY (PostId) REFERENCES posts(Id),
            FOREIGN KEY (UserId) REFERENCES users(Id)
        );
        """)
