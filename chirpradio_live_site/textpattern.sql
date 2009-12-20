-- phpMyAdmin SQL Dump
-- version 2.11.0
-- http://www.phpmyadmin.net
--
-- Host: internal-db.s49693.gridserver.com
-- Generation Time: Dec 20, 2009 at 10:04 AM
-- Server version: 5.0.51
-- PHP Version: 4.4.8

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";

--
-- Database: `db49693_chirpradio_txp`
--

-- --------------------------------------------------------

--
-- Table structure for table `textpattern`
--

CREATE TABLE `textpattern` (
  `ID` int(11) NOT NULL auto_increment,
    `Posted` datetime NOT NULL default '0000-00-00 00:00:00',
      `Expires` datetime NOT NULL default '0000-00-00 00:00:00',
        `AuthorID` varchar(64) NOT NULL default '',
          `LastMod` datetime NOT NULL default '0000-00-00 00:00:00',
            `LastModID` varchar(64) NOT NULL default '',
              `Title` varchar(255) NOT NULL default '',
                `Title_html` varchar(255) NOT NULL default '',
                  `Body` mediumtext NOT NULL,
                    `Body_html` mediumtext NOT NULL,
                      `Excerpt` text NOT NULL,
                        `Excerpt_html` mediumtext NOT NULL,
                          `Image` varchar(255) NOT NULL default '',
                            `Category1` varchar(128) NOT NULL default '',
                              `Category2` varchar(128) NOT NULL default '',
                                `Annotate` int(2) NOT NULL default '0',
                                  `AnnotateInvite` varchar(255) NOT NULL default '',
                                    `comments_count` int(8) NOT NULL default '0',
                                      `Status` int(2) NOT NULL default '4',
                                        `textile_body` int(2) NOT NULL default '1',
                                          `textile_excerpt` int(2) NOT NULL default '1',
                                            `Section` varchar(64) NOT NULL default '',
                                              `override_form` varchar(255) NOT NULL default '',
                                                `Keywords` varchar(255) NOT NULL default '',
                                                  `url_title` varchar(255) NOT NULL default '',
                                                    `custom_1` varchar(255) NOT NULL default '',
                                                      `custom_2` varchar(255) NOT NULL default '',
                                                        `custom_3` varchar(255) NOT NULL default '',
                                                          `custom_4` varchar(255) NOT NULL default '',
                                                            `custom_5` varchar(255) NOT NULL default '',
                                                              `custom_6` varchar(255) NOT NULL default '',
                                                                `custom_7` varchar(255) NOT NULL default '',
                                                                  `custom_8` varchar(255) NOT NULL default '',
                                                                    `custom_9` varchar(255) NOT NULL default '',
                                                                      `custom_10` varchar(255) NOT NULL default '',
                                                                        `uid` varchar(32) NOT NULL default '',
                                                                          `feed_time` date NOT NULL default '0000-00-00',
                                                                            PRIMARY KEY  (`ID`),
                                                                              KEY `categories_idx` (`Category1`(10),`Category2`(10)),
                                                                                KEY `Posted` (`Posted`),
                                                                                  KEY `section_status_idx` (`Section`,`Status`),
                                                                                    KEY `Expires_idx` (`Expires`),
                                                                                      KEY `author_idx` (`AuthorID`),
                                                                                        FULLTEXT KEY `searching` (`Title`,`Body`)
                                                                                        ) ENGINE=MyISAM  DEFAULT CHARSET=utf8 PACK_KEYS=1 AUTO_INCREMENT=8 ;

                                                                                        --
                                                                                        -- Dumping data for table `textpattern`
                                                                                        --

                                                                                        INSERT INTO `textpattern` (`ID`, `Posted`, `Expires`, `AuthorID`, `LastMod`,
                                                                                        `LastModID`, `Title`, `Title_html`, `Body`, `Body_html`, `Excerpt`, `Excerpt_html`,
                                                                                        `Image`, `Category1`, `Category2`, `Annotate`, `AnnotateInvite`, `comments_count`,
                                                                                        `Status`, `textile_body`, `textile_excerpt`, `Section`, `override_form`, `Keywords`,
                                                                                        `url_title`, `custom_1`, `custom_2`, `custom_3`, `custom_4`, `custom_5`, `custom_6`,
                                                                                        `custom_7`, `custom_8`, `custom_9`, `custom_10`, `uid`, `feed_time`) VALUES
                                                                                        (1, '2008-09-02 06:31:18', '0000-00-00 00:00:00', 'lovehasnologic', '2008-09-02
                                                                                        06:31:18', '', 'First Post', '', 'Lorem ipsum dolor sit amet, consectetuer adipiscing
                                                                                        elit. Donec rutrum est eu mauris. In volutpat blandit felis. Suspendisse eget pede.
                                                                                        Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos
                                                                                        hymenaeos. Quisque sed arcu. Aenean purus nulla, condimentum ac, pretium at, commodo
                                                                                        sit amet, turpis. Aenean lacus. Ut in justo. Ut viverra dui vel ante. Duis imperdiet
                                                                                        porttitor mi. Maecenas at lectus eu justo porta tempus. Cras fermentum ligula non
                                                                                        purus. Duis id orci non magna rutrum bibendum. Mauris tincidunt, massa in rhoncus
                                                                                        consectetuer, lectus dui ornare enim, ut egestas ipsum purus id urna. Vestibulum
                                                                                        volutpat porttitor metus. Donec congue vehicula ante.', '       <p>Lorem ipsum dolor sit
                                                                                        amet, consectetuer adipiscing elit. Donec rutrum est eu mauris. In volutpat blandit
                                                                                        felis. Suspendisse eget pede. Class aptent taciti sociosqu ad litora torquent per
                                                                                        conubia nostra, per inceptos hymenaeos. Quisque sed arcu. Aenean purus nulla,
                                                                                        condimentum ac, pretium at, commodo sit amet, turpis. Aenean lacus. Ut in justo. Ut
                                                                                        viverra dui vel ante. Duis imperdiet porttitor mi. Maecenas at lectus eu justo porta
                                                                                        tempus. Cras fermentum ligula non purus. Duis id orci non magna rutrum bibendum.
                                                                                        Mauris tincidunt, massa in rhoncus consectetuer, lectus dui ornare enim, ut egestas
                                                                                        ipsum purus id urna. Vestibulum volutpat porttitor metus. Donec congue vehicula
                                                                                        ante.</p>\n\n\n ', '', '', '', 'hope-for-the-future', 'meaningful-labor', 1,
                                                                                        'Comment', 1, 4, 1, 1, 'playlists', '', '', 'first-post', '', '', '', '', '', '', '',
                                                                                        '', '', '', 'dce16e0ddd7f650567ce96a305682881', '2008-09-02'),
                                                                                        (2, '2009-12-17 17:46:32', '0000-00-00 00:00:00', 'lovehasnologic', '2009-12-17
                                                                                        12:58:23', 'lovehasnologic', 'The Boat Dreams From The Hill', '', '24 Hour Revenge
                                                                                        Therapy', '     <p>24 Hour Revenge Therapy</p>', 'Never playing again', '       <p>Never
                                                                                        playing again</p>', '', '', '', 0, 'Comment', 0, 4, 1, 1, 'playlists', '',
                                                                                        'Jawbreaker', '2-jawbreaker-the-boat-dreams-from-the-hill', 'Tupelo', 'Dustin Drase',
                                                                                        '', '', '', '', '', '', '', '', 'e84ff2c7abe5102372904ec19074c4a2', '2009-12-17'),
                                                                                        (3, '2009-12-17 12:48:42', '0000-00-00 00:00:00', 'lovehasnologic', '2009-12-17
                                                                                        12:58:07', 'lovehasnologic', 'Day Dangerous', '', 'Exiting Arm', '      <p>Exiting
                                                                                        Arm</p>', '', '', '', '', '', 0, 'Comment', 0, 4, 1, 1, 'playlists', '', 'Subtle',
                                                                                        '3-subtle-day-dangerous', 'Lex Records', 'Dustin Drase', '', '', '', '', '', '', '',
                                                                                        '', 'f1e284b6bee298d624a74136453583dc', '2009-12-17'),
                                                                                        (4, '2009-12-17 12:53:07', '0000-00-00 00:00:00', 'lovehasnologic', '2009-12-17
                                                                                        12:57:54', 'lovehasnologic', 'Hey, Is That A Ninja Up There', '', 'They Make Beer
                                                                                        Commercials Like This ', '      <p>They Make Beer Commercials Like This </p>', '', '', '',
                                                                                        '', '', 0, 'Comment', 0, 4, 1, 1, 'playlists', '', 'Minus The Bear',
                                                                                        '4-minus-the-bear-hey-is-that-a-ninja-up-there', 'Suicide Squeeze', 'Dustin Drase',
                                                                                        '', '', '', '', '', '', '', '', 'b12a9a78bb6e8c08488f58737bc94bc7', '2009-12-17'),
                                                                                        (5, '2009-12-17 12:54:14', '0000-00-00 00:00:00', 'lovehasnologic', '2009-12-17
                                                                                        12:57:35', 'lovehasnologic', 'A Finger To Hackle', '', 'Scratch or Stitch', '
                                                                                        <p>Scratch or Stitch</p>', '', '', '', '', '', 0, 'Comment', 0, 4, 1, 1, 'playlists',
                                                                                        '', 'Melt-Banana', '5-melt-banana-a-finger-to-hackle', 'GSL', 'Dustin Drase', '', '',
                                                                                        '', '', '', '', '', '', 'd70c5297287051f55f33cbe1790315c0', '2009-12-17'),
                                                                                        (6, '2009-12-17 12:54:54', '0000-00-00 00:00:00', 'lovehasnologic', '2009-12-17
                                                                                        12:57:18', 'lovehasnologic', 'Yellow, Blue and Green', '', 'Quetzalcoatl', '
                                                                                        <p>Quetzalcoatl</p>', 'R.I.P. Lance Hahn', '    <p>R.I.P. Lance Hahn</p>', '', '', '',
                                                                                        0, 'Comment', 0, 4, 1, 1, 'playlists', '', 'J Church',
                                                                                        '6-j-church-yellow-blue-and-green', 'Allied', 'Dustin Drase', '', '', '', '', '', '',
                                                                                        '', '', '60d268936e224816d878292f6a5a882f', '2009-12-17'),
                                                                                        (7, '2009-12-17 12:55:38', '0000-00-00 00:00:00', 'lovehasnologic', '2009-12-17
                                                                                        12:57:01', 'lovehasnologic', 'Escape From New Rock', '', 'A+ Electric', '       <p>A+
                                                                                        Electric</p>', '', '', '', '', '', 0, 'Comment', 0, 4, 1, 1, 'playlists', '',
                                                                                        'Crushstory', '7-crushstory-escape-from-new-rock', 'Pop Kid Records', 'Dustin Drase',
                                                                                        '', '', '', '', '', '', '', '', '70f98e1397419e954e8c03ee879e21b5', '2009-12-17');

