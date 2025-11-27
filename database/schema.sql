-- --------------------------------------------------------
-- Host:                         relational.fel.cvut.cz
-- Server version:               10.6.12-MariaDB-1:10.6.12+maria~ubu2004-log - mariadb.org binary distribution
-- Server OS:                    debian-linux-gnu
-- HeidiSQL Version:             12.11.0.7065
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for stats
CREATE DATABASE IF NOT EXISTS `stats` /*!40100 DEFAULT CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci */;
USE `stats`;

-- Dumping structure for table stats.badges
CREATE TABLE IF NOT EXISTS `badges` (
  `Id` int(11) NOT NULL,
  `UserId` int(11) DEFAULT NULL,
  `Name` varchar(255) DEFAULT NULL,
  `Date` datetime DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `badges_UserId_fkey` (`UserId`),
  CONSTRAINT `badges_UserId_fkey` FOREIGN KEY (`UserId`) REFERENCES `users` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

-- Dumping structure for table stats.comments
CREATE TABLE IF NOT EXISTS `comments` (
  `Id` int(11) NOT NULL,
  `PostId` int(11) DEFAULT NULL,
  `Score` int(11) DEFAULT NULL,
  `Text` longtext DEFAULT NULL,
  `CreationDate` datetime DEFAULT NULL,
  `UserId` int(11) DEFAULT NULL,
  `UserDisplayName` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `comment_staged_UserId_fkey` (`UserId`),
  KEY `comment_PostId_fkey` (`PostId`),
  CONSTRAINT `comment_PostId_fkey` FOREIGN KEY (`PostId`) REFERENCES `posts` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `comment_staged_UserId_fkey` FOREIGN KEY (`UserId`) REFERENCES `users` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

-- Dumping structure for table stats.postHistory
CREATE TABLE IF NOT EXISTS `postHistory` (
  `Id` int(11) NOT NULL,
  `PostHistoryTypeId` int(11) DEFAULT NULL,
  `PostId` int(11) DEFAULT NULL,
  `RevisionGUID` varchar(255) DEFAULT NULL,
  `CreationDate` datetime DEFAULT NULL,
  `UserId` int(11) DEFAULT NULL,
  `Text` longtext DEFAULT NULL,
  `Comment` text DEFAULT NULL,
  `UserDisplayName` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `postHistory_Id_key` (`Id`),
  KEY `postHistory_UserId_fkey` (`UserId`),
  KEY `postHistory_PostId_fkey` (`PostId`),
  CONSTRAINT `postHistory_PostId_fkey` FOREIGN KEY (`PostId`) REFERENCES `posts` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `postHistory_UserId_fkey` FOREIGN KEY (`UserId`) REFERENCES `users` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

-- Dumping structure for table stats.postLinks
CREATE TABLE IF NOT EXISTS `postLinks` (
  `Id` int(11) NOT NULL,
  `CreationDate` datetime DEFAULT NULL,
  `PostId` int(11) DEFAULT NULL,
  `RelatedPostId` int(11) DEFAULT NULL,
  `LinkTypeId` int(11) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `postlinks_stripped_PostId_fkey` (`PostId`),
  KEY `postlinks_stripped_RelatedPostId_fkey` (`RelatedPostId`),
  CONSTRAINT `postlinks_stripped_PostId_fkey` FOREIGN KEY (`PostId`) REFERENCES `posts` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `postlinks_stripped_RelatedPostId_fkey` FOREIGN KEY (`RelatedPostId`) REFERENCES `posts` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

-- Dumping structure for table stats.posts
CREATE TABLE IF NOT EXISTS `posts` (
  `Id` int(11) NOT NULL,
  `PostTypeId` int(11) DEFAULT NULL,
  `AcceptedAnswerId` int(11) DEFAULT NULL,
  `CreaionDate` datetime DEFAULT NULL,
  `Score` int(11) DEFAULT NULL,
  `ViewCount` int(11) DEFAULT NULL,
  `Body` longtext DEFAULT NULL,
  `OwnerUserId` int(11) DEFAULT NULL,
  `LasActivityDate` datetime DEFAULT NULL,
  `Title` varchar(255) DEFAULT NULL,
  `Tags` varchar(255) DEFAULT NULL,
  `AnswerCount` int(11) DEFAULT NULL,
  `CommentCount` int(11) DEFAULT NULL,
  `FavoriteCount` int(11) DEFAULT NULL,
  `LastEditorUserId` int(11) DEFAULT NULL,
  `LastEditDate` datetime DEFAULT NULL,
  `CommunityOwnedDate` datetime DEFAULT NULL,
  `ParentId` int(11) DEFAULT NULL,
  `ClosedDate` datetime DEFAULT NULL,
  `OwnerDisplayName` varchar(255) DEFAULT NULL,
  `LastEditorDisplayName` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `posts_Id_key` (`Id`),
  KEY `posts_ParentId_fkey` (`ParentId`),
  KEY `posts_OwnerUserId_fkey` (`OwnerUserId`),
  KEY `posts_LastEditorUserId_fkey` (`LastEditorUserId`),
  CONSTRAINT `posts_LastEditorUserId_fkey` FOREIGN KEY (`LastEditorUserId`) REFERENCES `users` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `posts_OwnerUserId_fkey` FOREIGN KEY (`OwnerUserId`) REFERENCES `users` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `posts_ParentId_fkey` FOREIGN KEY (`ParentId`) REFERENCES `posts` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

-- Dumping structure for table stats.tags
CREATE TABLE IF NOT EXISTS `tags` (
  `Id` int(11) NOT NULL,
  `TagName` varchar(255) DEFAULT NULL,
  `Count` int(11) DEFAULT NULL,
  `ExcerptPostId` int(11) DEFAULT NULL,
  `WikiPostId` int(11) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `tags_ExcerptPostId_fkey` (`ExcerptPostId`),
  CONSTRAINT `tags_ExcerptPostId_fkey` FOREIGN KEY (`ExcerptPostId`) REFERENCES `posts` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

-- Dumping structure for table stats.users
CREATE TABLE IF NOT EXISTS `users` (
  `Id` int(11) NOT NULL,
  `Reputation` int(11) DEFAULT NULL,
  `CreationDate` datetime DEFAULT NULL,
  `DisplayName` varchar(255) DEFAULT NULL,
  `LastAccessDate` datetime DEFAULT NULL,
  `WebsiteUrl` varchar(255) DEFAULT NULL,
  `Location` varchar(255) DEFAULT NULL,
  `AboutMe` longtext DEFAULT NULL,
  `Views` int(11) DEFAULT NULL,
  `UpVotes` int(11) DEFAULT NULL,
  `DownVotes` int(11) DEFAULT NULL,
  `AccountId` int(11) DEFAULT NULL,
  `Age` int(11) DEFAULT NULL,
  `ProfileImageUrl` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `users_staged_Id_key` (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

-- Dumping structure for table stats.votes
CREATE TABLE IF NOT EXISTS `votes` (
  `Id` int(11) NOT NULL,
  `PostId` int(11) DEFAULT NULL,
  `VoteTypeId` int(11) DEFAULT NULL,
  `CreationDate` date DEFAULT NULL,
  `UserId` int(11) DEFAULT NULL,
  `BountyAmount` int(11) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `votes_stripped_UserId_fkey` (`UserId`),
  KEY `votes_stripped_PostId_fkey` (`PostId`),
  CONSTRAINT `votes_stripped_PostId_fkey` FOREIGN KEY (`PostId`) REFERENCES `posts` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `votes_stripped_UserId_fkey` FOREIGN KEY (`UserId`) REFERENCES `users` (`Id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- Data exporting was unselected.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
