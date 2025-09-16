CREATE DATABASE  IF NOT EXISTS `dateaubase` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `dateaubase`;
-- MySQL dump 10.13  Distrib 5.7.9, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: dateaubase
-- ------------------------------------------------------
-- Server version	5.7.11-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `comments`
--

DROP TABLE IF EXISTS `comments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `comments` (
  `Comment_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Comment` text NOT NULL,
  PRIMARY KEY (`Comment_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `comments`
--

LOCK TABLES `comments` WRITE;
/*!40000 ALTER TABLE `comments` DISABLE KEYS */;
/*!40000 ALTER TABLE `comments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `contact`
--

DROP TABLE IF EXISTS `contact`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `contact` (
  `Contact_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Last_name` varchar(100) NOT NULL,
  `First_name` tinytext NOT NULL,
  `Company` text NOT NULL,
  `Status` tinytext NOT NULL,
  `Function` text NOT NULL,
  `Office_number` varchar(100) NOT NULL,
  `Email` varchar(100) NOT NULL,
  `Phone` varchar(100) NOT NULL,
  `Skype_name` varchar(100) DEFAULT 'None',
  `Linkedin` varchar(100) DEFAULT 'None',
  `Street_number` varchar(100) NOT NULL,
  `Street_name` varchar(100) NOT NULL,
  `City` tinytext NOT NULL,
  `Zip_code` varchar(45) NOT NULL,
  `Province` tinytext NOT NULL,
  `Country` tinytext NOT NULL,
  PRIMARY KEY (`Contact_ID`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `contact`
--

LOCK TABLES `contact` WRITE;
/*!40000 ALTER TABLE `contact` DISABLE KEYS */;
INSERT INTO `contact` VALUES (1,'Patry','Bernard','Université Laval','','PhD student','PLT-2983_159','bernard.patry.1@ulaval.ca','418-928-6893','bernard.patry1','None','1300','Saint-Jean','Saint-Hyacinthe','J2S 8M3','Québec','Canada');
/*!40000 ALTER TABLE `contact` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `equipment`
--

DROP TABLE IF EXISTS `equipment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `equipment` (
  `Equipment_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Equipment_identifier` varchar(100) NOT NULL,
  `Serial_number` varchar(100) NOT NULL,
  `Owner` text NOT NULL,
  `Storage_location` varchar(100) NOT NULL,
  `Purchase_date` date NOT NULL,
  `Equipment_model_ID` int(11) NOT NULL,
  PRIMARY KEY (`Equipment_ID`),
  KEY `fk_Equipment_Equipment_model1_idx` (`Equipment_model_ID`),
  CONSTRAINT `fk_Equipment_Equipment_model1` FOREIGN KEY (`Equipment_model_ID`) REFERENCES `equipment_model` (`Equipment_model_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `equipment`
--

LOCK TABLES `equipment` WRITE;
/*!40000 ALTER TABLE `equipment` DISABLE KEYS */;
/*!40000 ALTER TABLE `equipment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `equipment_model`
--

DROP TABLE IF EXISTS `equipment_model`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `equipment_model` (
  `Equipment_model_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Equipment_model` varchar(100) NOT NULL,
  `Method` varchar(100) NOT NULL,
  `Functions` text NOT NULL,
  `Manufacturer` varchar(100) NOT NULL,
  `Manual_location` varchar(100) NOT NULL,
  PRIMARY KEY (`Equipment_model_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `equipment_model`
--

LOCK TABLES `equipment_model` WRITE;
/*!40000 ALTER TABLE `equipment_model` DISABLE KEYS */;
/*!40000 ALTER TABLE `equipment_model` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `equipment_model_has_parameter`
--

DROP TABLE IF EXISTS `equipment_model_has_parameter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `equipment_model_has_parameter` (
  `Equipment_model_ID` int(11) NOT NULL,
  `Parameter_ID` int(11) NOT NULL,
  PRIMARY KEY (`Equipment_model_ID`,`Parameter_ID`),
  KEY `fk_Equipment_model_has_Parameter_Parameter1_idx` (`Parameter_ID`),
  KEY `fk_Equipment_model_has_Parameter_Equipment_model1_idx` (`Equipment_model_ID`),
  CONSTRAINT `fk_Equipment_model_has_Parameter_Equipment_model1` FOREIGN KEY (`Equipment_model_ID`) REFERENCES `equipment_model` (`Equipment_model_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Equipment_model_has_Parameter_Parameter1` FOREIGN KEY (`Parameter_ID`) REFERENCES `parameter` (`Parameter_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `equipment_model_has_parameter`
--

LOCK TABLES `equipment_model_has_parameter` WRITE;
/*!40000 ALTER TABLE `equipment_model_has_parameter` DISABLE KEYS */;
/*!40000 ALTER TABLE `equipment_model_has_parameter` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `equipment_model_has_procedures`
--

DROP TABLE IF EXISTS `equipment_model_has_procedures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `equipment_model_has_procedures` (
  `Equipment_model_ID` int(11) NOT NULL,
  `Procedure_ID` int(11) NOT NULL,
  PRIMARY KEY (`Equipment_model_ID`,`Procedure_ID`),
  KEY `fk_Equipment_model_has_Procedures_Procedures1_idx` (`Procedure_ID`),
  KEY `fk_Equipment_model_has_Procedures_Equipment_model1_idx` (`Equipment_model_ID`),
  CONSTRAINT `fk_Equipment_model_has_Procedures_Equipment_model1` FOREIGN KEY (`Equipment_model_ID`) REFERENCES `equipment_model` (`Equipment_model_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Equipment_model_has_Procedures_Procedures1` FOREIGN KEY (`Procedure_ID`) REFERENCES `procedures` (`Procedure_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `equipment_model_has_procedures`
--

LOCK TABLES `equipment_model_has_procedures` WRITE;
/*!40000 ALTER TABLE `equipment_model_has_procedures` DISABLE KEYS */;
/*!40000 ALTER TABLE `equipment_model_has_procedures` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `hydrological_characteristics`
--

DROP TABLE IF EXISTS `hydrological_characteristics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `hydrological_characteristics` (
  `Watershed_ID` int(11) NOT NULL,
  `Urban_area` float NOT NULL,
  `Forest` float NOT NULL,
  `Wetlands` float NOT NULL,
  `Cropland` float NOT NULL,
  `Meadow` float NOT NULL,
  `Grassland` float NOT NULL,
  PRIMARY KEY (`Watershed_ID`),
  KEY `fk_Hydrological_Land_Use_Watershed1_idx` (`Watershed_ID`),
  CONSTRAINT `fk_Hydrological_Land_Use_Watershed1` FOREIGN KEY (`Watershed_ID`) REFERENCES `watershed` (`Watershed_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hydrological_characteristics`
--

LOCK TABLES `hydrological_characteristics` WRITE;
/*!40000 ALTER TABLE `hydrological_characteristics` DISABLE KEYS */;
/*!40000 ALTER TABLE `hydrological_characteristics` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `metadata`
--

DROP TABLE IF EXISTS `metadata`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `metadata` (
  `Metadata_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Parameter_ID` int(11) DEFAULT NULL,
  `Unit_ID` int(11) DEFAULT NULL,
  `Purpose_ID` int(11) DEFAULT NULL,
  `Equipment_ID` int(11) DEFAULT NULL,
  `Procedure_ID` int(11) DEFAULT NULL,
  `Condition_ID` int(11) DEFAULT NULL,
  `Sampling_point_ID` int(11) DEFAULT NULL,
  `Contact_ID` int(11) NOT NULL,
  `Project_ID` int(11) DEFAULT NULL,
  PRIMARY KEY (`Metadata_ID`),
  KEY `fk_Information_Sampling-point1_idx` (`Sampling_point_ID`),
  KEY `fk_Information_Contact1_idx` (`Contact_ID`),
  KEY `fk_Information_Parameter1_idx` (`Parameter_ID`),
  KEY `fk_Meta-Data_Procedure1_idx` (`Procedure_ID`),
  KEY `fk_Meta-Data_Project1_idx` (`Project_ID`),
  KEY `fk_Metadata_Unit1_idx` (`Unit_ID`),
  KEY `fk_Metadata_Weather_condition1_idx` (`Condition_ID`),
  KEY `fk_Metadata_Equipment1_idx` (`Equipment_ID`),
  KEY `fk_Metadata_Purpose1_idx` (`Purpose_ID`),
  CONSTRAINT `fk_Information_Contact1` FOREIGN KEY (`Contact_ID`) REFERENCES `contact` (`Contact_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Information_Parameter1` FOREIGN KEY (`Parameter_ID`) REFERENCES `parameter` (`Parameter_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Information_Sampling-point1` FOREIGN KEY (`Sampling_point_ID`) REFERENCES `sampling_points` (`Sampling_point_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Meta-Data_Procedure1` FOREIGN KEY (`Procedure_ID`) REFERENCES `procedures` (`Procedure_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Meta-Data_Project1` FOREIGN KEY (`Project_ID`) REFERENCES `project` (`Project_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Metadata_Equipment1` FOREIGN KEY (`Equipment_ID`) REFERENCES `equipment` (`Equipment_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Metadata_Purpose1` FOREIGN KEY (`Purpose_ID`) REFERENCES `purpose` (`Purpose_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Metadata_Unit1` FOREIGN KEY (`Unit_ID`) REFERENCES `unit` (`Unit_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Metadata_Weather_condition1` FOREIGN KEY (`Condition_ID`) REFERENCES `weather_condition` (`Condition_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `metadata`
--

LOCK TABLES `metadata` WRITE;
/*!40000 ALTER TABLE `metadata` DISABLE KEYS */;
/*!40000 ALTER TABLE `metadata` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `parameter`
--

DROP TABLE IF EXISTS `parameter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `parameter` (
  `Parameter_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Parameter` varchar(100) NOT NULL,
  `Unit_ID` int(11) NOT NULL,
  `Description` text NOT NULL,
  PRIMARY KEY (`Parameter_ID`),
  KEY `fk_Parameter_Unit1_idx` (`Unit_ID`),
  CONSTRAINT `fk_Parameter_Unit1` FOREIGN KEY (`Unit_ID`) REFERENCES `unit` (`Unit_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `parameter`
--

LOCK TABLES `parameter` WRITE;
/*!40000 ALTER TABLE `parameter` DISABLE KEYS */;
/*!40000 ALTER TABLE `parameter` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `parameter_has_procedures`
--

DROP TABLE IF EXISTS `parameter_has_procedures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `parameter_has_procedures` (
  `Parameter_ID` int(11) NOT NULL,
  `Procedure_ID` int(11) NOT NULL,
  PRIMARY KEY (`Parameter_ID`,`Procedure_ID`),
  KEY `fk_Parameter_has_Procedures_Procedures1_idx` (`Procedure_ID`),
  KEY `fk_Parameter_has_Procedures_Parameter1_idx` (`Parameter_ID`),
  CONSTRAINT `fk_Parameter_has_Procedures_Parameter1` FOREIGN KEY (`Parameter_ID`) REFERENCES `parameter` (`Parameter_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Parameter_has_Procedures_Procedures1` FOREIGN KEY (`Procedure_ID`) REFERENCES `procedures` (`Procedure_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `parameter_has_procedures`
--

LOCK TABLES `parameter_has_procedures` WRITE;
/*!40000 ALTER TABLE `parameter_has_procedures` DISABLE KEYS */;
/*!40000 ALTER TABLE `parameter_has_procedures` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `procedures`
--

DROP TABLE IF EXISTS `procedures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `procedures` (
  `Procedure_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Procedure_name` varchar(100) NOT NULL,
  `Procedure_type` tinytext NOT NULL,
  `Description` text NOT NULL,
  `Procedure_location` varchar(100) NOT NULL,
  PRIMARY KEY (`Procedure_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `procedures`
--

LOCK TABLES `procedures` WRITE;
/*!40000 ALTER TABLE `procedures` DISABLE KEYS */;
/*!40000 ALTER TABLE `procedures` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `project`
--

DROP TABLE IF EXISTS `project`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `project` (
  `Project_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Project_name` varchar(100) NOT NULL,
  `Description` text NOT NULL,
  PRIMARY KEY (`Project_ID`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `project`
--

LOCK TABLES `project` WRITE;
/*!40000 ALTER TABLE `project` DISABLE KEYS */;
INSERT INTO `project` VALUES (1,'kamEAU','KAMAK wastewater treatment train (aerated lagoon enhancement system) monitoring, understanding, modelling and improving');
/*!40000 ALTER TABLE `project` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `project_has_contact`
--

DROP TABLE IF EXISTS `project_has_contact`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `project_has_contact` (
  `Project_ID` int(11) NOT NULL,
  `Contact_ID` int(11) NOT NULL,
  PRIMARY KEY (`Project_ID`,`Contact_ID`),
  KEY `fk_Project_has_Contact_Contact1_idx` (`Contact_ID`),
  KEY `fk_Project_has_Contact_Project1_idx` (`Project_ID`),
  CONSTRAINT `fk_Project_has_Contact_Contact1` FOREIGN KEY (`Contact_ID`) REFERENCES `contact` (`Contact_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Project_has_Contact_Project1` FOREIGN KEY (`Project_ID`) REFERENCES `project` (`Project_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `project_has_contact`
--

LOCK TABLES `project_has_contact` WRITE;
/*!40000 ALTER TABLE `project_has_contact` DISABLE KEYS */;
INSERT INTO `project_has_contact` VALUES (1,1);
/*!40000 ALTER TABLE `project_has_contact` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `project_has_equipment`
--

DROP TABLE IF EXISTS `project_has_equipment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `project_has_equipment` (
  `Project_ID` int(11) NOT NULL,
  `Equipment_ID` int(11) NOT NULL,
  PRIMARY KEY (`Project_ID`,`Equipment_ID`),
  KEY `fk_Project_has_Equipment_Equipment1_idx` (`Equipment_ID`),
  KEY `fk_Project_has_Equipment_Project1_idx` (`Project_ID`),
  CONSTRAINT `fk_Project_has_Equipment_Equipment1` FOREIGN KEY (`Equipment_ID`) REFERENCES `equipment` (`Equipment_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Project_has_Equipment_Project1` FOREIGN KEY (`Project_ID`) REFERENCES `project` (`Project_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `project_has_equipment`
--

LOCK TABLES `project_has_equipment` WRITE;
/*!40000 ALTER TABLE `project_has_equipment` DISABLE KEYS */;
/*!40000 ALTER TABLE `project_has_equipment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `project_has_sampling_points`
--

DROP TABLE IF EXISTS `project_has_sampling_points`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `project_has_sampling_points` (
  `Project_ID` int(11) NOT NULL,
  `Sampling_point_ID` int(11) NOT NULL,
  PRIMARY KEY (`Project_ID`,`Sampling_point_ID`),
  KEY `fk_Project_has_Sampling-point_Sampling-point1_idx` (`Sampling_point_ID`),
  KEY `fk_Project_has_Sampling-point_Project1_idx` (`Project_ID`),
  CONSTRAINT `fk_Project_has_Sampling-point_Project1` FOREIGN KEY (`Project_ID`) REFERENCES `project` (`Project_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Project_has_Sampling-point_Sampling-point1` FOREIGN KEY (`Sampling_point_ID`) REFERENCES `sampling_points` (`Sampling_point_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `project_has_sampling_points`
--

LOCK TABLES `project_has_sampling_points` WRITE;
/*!40000 ALTER TABLE `project_has_sampling_points` DISABLE KEYS */;
INSERT INTO `project_has_sampling_points` VALUES (1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),(1,8),(1,9),(1,10);
/*!40000 ALTER TABLE `project_has_sampling_points` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `purpose`
--

DROP TABLE IF EXISTS `purpose`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `purpose` (
  `Purpose_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Purpose` varchar(100) NOT NULL,
  `Description` text NOT NULL,
  PRIMARY KEY (`Purpose_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purpose`
--

LOCK TABLES `purpose` WRITE;
/*!40000 ALTER TABLE `purpose` DISABLE KEYS */;
/*!40000 ALTER TABLE `purpose` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sampling_points`
--

DROP TABLE IF EXISTS `sampling_points`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sampling_points` (
  `Sampling_point_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Sampling_point` varchar(100) NOT NULL,
  `Sampling_location` varchar(100) DEFAULT NULL,
  `Site_ID` int(11) NOT NULL,
  `Latitude_GPS` varchar(100) NOT NULL,
  `Longitude_GPS` varchar(100) NOT NULL,
  `Description` text NOT NULL,
  `Picture` blob,
  PRIMARY KEY (`Sampling_point_ID`),
  KEY `fk_Sampling-point_Site1_idx` (`Site_ID`),
  CONSTRAINT `fk_Sampling-point_Site1` FOREIGN KEY (`Site_ID`) REFERENCES `site` (`Site_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sampling_points`
--

LOCK TABLES `sampling_points` WRITE;
/*!40000 ALTER TABLE `sampling_points` DISABLE KEYS */;
INSERT INTO `sampling_points` VALUES (1,'CL1_AFF','Clarifier number 1 affluent',1,'0','0','Clarifier number 1 affluent',NULL),(2,'CL1_EFF','Clarifier number 1 effluent',1,'0','0','Clarifier number 1 effluent',NULL),(3,'RX1_AFF','Reactor number 1 affluent',1,'0','0','Reactor number 1 affluent',NULL),(4,'RX1_EFF','Reactor number 1 effluent',1,'0','0','Reactor number 1 effluent',NULL),(5,'CL2_AFF','Clarifier number 2 affluent',1,'0','0','Clarifier number 2 affluent',NULL),(6,'CL2_EFF','Clarifier number 2 effluent',1,'0','0','Clarifier number 2 effluent',NULL),(7,'RX2_AFF','Reactor number 2 affluent',1,'0','0','Reactor number 2 affluent',NULL),(8,'RX2_EFF','Reactor number 2 effluent',1,'0','0','Reactor number 2 effluent',NULL),(9,'CL3_AFF','Clarifier number 3 affluent',1,'0','0','Clarifier number 3 affluent',NULL),(10,'CL3_EFF','Clarifier number 3 effluent',1,'0','0','Clarifier number 3 effluent',NULL);
/*!40000 ALTER TABLE `sampling_points` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `site`
--

DROP TABLE IF EXISTS `site`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `site` (
  `Site_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Site_name` varchar(100) NOT NULL,
  `Site_type` tinytext NOT NULL,
  `Watershed_ID` int(11) DEFAULT NULL,
  `Description` text NOT NULL,
  `Picture` blob,
  `Street_number` varchar(100) DEFAULT 'None',
  `Street_name` varchar(100) DEFAULT 'None',
  `City` tinytext,
  `Zip_code` varchar(100) DEFAULT 'None',
  `Province` tinytext NOT NULL,
  `Country` tinytext NOT NULL,
  PRIMARY KEY (`Site_ID`),
  KEY `fk_Site_Watershed1_idx` (`Watershed_ID`),
  CONSTRAINT `fk_Site_Watershed1` FOREIGN KEY (`Watershed_ID`) REFERENCES `watershed` (`Watershed_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `site`
--

LOCK TABLES `site` WRITE;
/*!40000 ALTER TABLE `site` DISABLE KEYS */;
INSERT INTO `site` VALUES (1,'Grandes-Piles wastewater treatment plant','Wastewater treatment plant',1,'Aerated lagoon with Bionest R&D installations (KAMAK)','�\��\�\0JFIF\0\0�\0�\0\0�\�\0C\0\n	\n		\n$ &%# #\"(-90(*6+\"#2D26;=@@@&0FKE>J9?@=�\�\0C\r=)#)==================================================��\0�\�\"\0�\�\0\0\0\0\0\0\0\0\0\0\0	\n�\�\0�\0\0\0}\0!1AQa\"q2���#B��R\��$3br�	\n\Z%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz�����������������������������������\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\������������\�\0\0\0\0\0\0\0\0	\n�\�\0�\0\0w\0!1AQaq\"2�B����	#3R�br\�\n$4\�%�\Z&\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz������������������������������������\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�\�����������\�\0\0\0?\0��p��zm\�s�\�\�K\�7�G�QJȫ�ŉ\�I�}i\��u���CJ�\\�+v�\nކ�P��\���\�W)_,:�I�>�`�Lgҕ\�\�J6�`\�\�\rM\�\�\�K\�SG0Y���@��\��\\\�\\���1S���\�y\rG2+!\��|�\�S�#ގd��b��\�Hm�\r\�9Y_b�08��\�v4\�+2:)أ\�%��\0�R\�\0J)h\�\0%\�Q�@\r\��\�\0�R\�\0(�b�b���\�4�c(\�H\"cڃ\�]̎�qR;Rb�\�6�Z(�R\�P1��b�PQK�1N\�%%;m4\\\�N\�}(\�}(�Xm��\�`��Q�\0m%;��\�N\��!�b�b��Q�\\Q�.;	�)qF(��7S�IE�J(���E-(Bh��0�=\�;\�^\�2++\�U�%=M\'���s��2�c\�Aޏ.?z9\�r2�)*ϗ��bzQ\����J�寥4Ħ�p\�eS\�\n*G�\�=�!B=*���Z�(b�����@\�!>��R)}\��ܵa\�/SK\�/zf\��\�v\�\�E�\�ҏ)Oj@\�:\�\�\�KP\�_/\r0���/�(\�z\r.õ �\�S��\�A1�\�ůq\�ӄ�\�ldS1Nɓ\�\�dJ(�j�.\�;\�\�9?�K\�\�}\�ѓG(s�<\�I\�Ps\�J�4r�\�d�`�����o\�R�4Xwc�\�Q 5\�і�4X\\̗(z\�df�\�֎}h�_\�y�C�a@;\�\�>����\�QO�\�v�\�ޔ\�M�\�R��ޣ����-�\r\'�KN��\'j]�z��#��\�\�\�\Z�R~C�%&\�4\�-\�\\�T�u\�\�@�)OzkDz֑�\��Bbi�\�%=��B*\�E�T��*\Z2zRhiر\�\n�w��\�\�\r.R�\��\�|��XQ�\�\�ĥ#>\�(tӲ\\\�v�\�5�.̏b���&\�i)\�m�\�a�R�I@\0\�OVҙE\0�\'�G�\�QъVC�\�jeH\�\\qO`�\�Jv)1LA�@#҂(\�\080����\�Q�\��\���e�H#SHa�M�3\�)C��\�i�\�\�I�:�Rކ�\�\Zw��S\�M {Ձ�\�h\��R\�R�)1Vp?�M*j�ar\�\�!�\\R��\�\�\�\\��Fj�7��v�̅\�ȲGz]\�֔����z�\�>��\�֌Rb�\�]\�\�G�Ԕ��@�\�i\�7�l\�~h;�\�a��>��\�\�B���NzӍ6%�\�\'�J�\�=\rC�!d\rEHE\�\"\�W���C��SH�\0Ebh?jZM��Oiw5d&\�=\��ϵ.�o>���\�U�h�\�(l�O�B:�\�\�vB�\�<�\�E2G\�P�c�&�W\��k\�ꂍѰ銬���j@H(h.J#�\�l\���hoZQ!\�j\Z����\�Q���$>���+\0=)j6;\�<\�s���]O֚X�\�c6{\�\�\�i�1c{�Q��T,\��a�f$\�E�\�0�ᦙGu�\�\�T\�L\�?��D\\œ0�\� �9������>By��y=��Ҩ�\�@�\��\�]37�\'\�zUS)\�0\�{\�\�\�ߵ�\�@�n���%&��D.sP^�R��}\�+~h\�}\�{4>vi��3�)\�iV\�s�VXozx���{4\��\�F\�\�lU1���O ����)2���y\�S|\�h\�a΍!#\�9�ER�Ȥ�>@\�.��\��� U/<�<\�{\�\�.d]\�:��΄�\0�[��zQ\�\�\�2\�1	\�\�U`�҈\�b)Xd\�P?u���MH�zxV��q\�\"4�Q�\�i~oZ.Õ\rz�^��\�v�\�\�x�\�,�C\�G�=hi��s\�ad7\���R\�\�\�I��+�\�\��h$\nM\�Ҁ#���\�\��4���v���\�G���\�O+�������\�ޣAjbԛ\�R�j;\��\�F���j�\�抍�#\��\0:o�\�\�S��q ��\�U|���H���P\�&=����Q�M<CHs\�if\�\�&\��4�͎)�9��!B�\�:x\�\�:�\�K���	O�FA��i\�=\�\0�sI�Լw�+\�N\����qO��%E+�\�9\�)|�\�,s��/\�Lg�=CA\�H\'\�SZc�\�)�h��u6Nh\�Z���7B)Z �����P�$�g��\�S��m\�ҝ�h\\h�\�\n*�^I\�\�\�m͊(���4ę�\�P��\�\�\\\���sP�isE�\�M��\�9�ɢ�rM\��g\�Ty\�X.HOғ�jeX.H6�\\Z��4X.K�\�J\0���FiX.K����\0�\�3FM�\�?�I�=W\�\�M�\"?LR\�3QsN\�;\�\�_օR��)?G��vG�!\�M������./J))�\�.>\�A\�\�n4�4�\rl\�\�ւ���i\� u�\Z1@i�H\'�-%;�Y\r�8QK��?*Z(�?qh	ꋊ}-�ꂚm\�=2)\��ǡ\�\��\�G��\Z� ��8�\�VDF=8�\�Z��wab\0��\��5]��� w4\��S\�ǵ8��N\�}(\�})\Zx�Zf(��v<ɚ��e��q\���\�74f��vWҐ�JLњaqs\�h$z�nis@\\2;\��\�RQ`�\�SAL��\�\�\�`�Q�{\��\�J>�n\����|\��I�\�n����\0ѴP\0\�R\�zSN=(��\�ag���z\Zi��G\�=i~\�ý;ҙ���:��jwڏ���cҔƾ��\ZQ\�`z�PU�\�{�;`���\�\�Pzѷ=�ǵ\'J\0v\�\�)\nj�[�aǛ*�zn`3Xw\�2\�,\�x\�S+*\�\�\�@\�scSZ3�Ҹ-C\�S�\�\�(��\�5�y\�Z\�\n�\�?�\�q�\�q�Sb劀;�Tn5;x\�渄 ��\�W�\�k7��\�\�W_w8�o7A�\�\����\�wM��䛕!�Y6�zV.�\�\����H��]�b�Ɠ\�\�y=��W-�7Z\\\�9Qv�Y���\�4\�H\�⊠F@*M<\�v>���\�|\�p\�8\0U�X��RR\�1h��\0)i(\�\0-%�4\0��\�Z\0Z(\��(�4f�\n\rP0��J\0Z)(\�\0.h\�&i3Hf�\�sFi�\�\�IE\0--6����(\0��J\0Z))�i�̑<\�\r�=\�@\�LY�\��9�g&��h�I 0$s�\�$R��)S\�\Z\0u;��~\�\�bez�\�*����i\�Aqu\Z�&�\�\�\�\�\�\0jn����ǯ\�M1���Vū/3�7�=)\�|C\�a3|�8WڛGQ�9?��\\[4d�5ɏ\�o\n2�RdPC)����(\�|ik�\�6VX%ɗi\���\�gG.�ko\�y��\0A�W=)b\�\�f\�\�\�F\�\�2�\��\0Ux\�ֵ<�\Z�|��\�=�Ȫ��\�\�J�&`!C��Ɛ\�\n\�J�\�+�\�{R��8B˼��\��j6�\�\"J]�V	��gڵ?\�8�Y^\\��%\�\��\���.z\�sڢ�\�+u\�3�\�q\�p��\�8�(�k0�K;�9�w\�^)�Xdr,\\g?{��֍���oiWr2Ay2�H\�c��U�Xd\Z�\�d�ٕ\�\'�QZ�g��M,$p\\�D;���q&�l�(�+\��\0\�a^e\�3�\�N88\n�q[:ğ5\�7v\�P&P\'��!��\�F>�\�Zx\�\�\�\�\�գ�P�s\�p:b�!\�-gEt�6�����.\�VE\��\��\��l3\�ˏZ���1�Y\�~`H����RW/\�;X�P4l ?�{\Zl���\'Y\��1a\�^@\�z\�\�x\�23EyF�\�\�>�\�v\"��\�\�=�)��TX\�J\r�\�f\�$g8>\�\\,z\�A8\�Ȣ��\�\�\�j��\�3\\�\�\�\�\��\0�V.� ]\�5��DE���Ó�]���\r.�^W/�uY��9\�-W������\�UM�B\�\'�\�Z.���\�!��\�ya��$G�\�E�\�i�,�,@f\n\0\�\�y%��5...#�u���\08��:\�\�Ɍ\�p��I\�1J\�|��œr�Ȭ��\�5(\�d�\�Hq�C^T<[��0{ٹm���oo\�{Ըi_~s�<\�\�Bq�\�\��\�f\�%m�D݌\�5\�\�w�-y3\��rsP�Z\�H\�S#\�\0�h\�A\�z�\�䷖PC�ם�\�\�\r\�\�\�t�A�<\�\�.N�Ƽ�{�5\�6I\�I�mR\�\�is�\�s/\�\�\���Ǐ��\'?J�/\�-O�E\�!۰�Mʊ\�<\�#\�s�x\�&\�\�6��\�\�t2x\�Yx���	�q\�}���\��V���[��@�6\�\��\�L\���3��cR9n��T�2ܗ\�7<\�䔨�,\�\�Tf}�pM@�w1A�S�EW*O�\�!�c�\�$ԎN\�s\�H�l��H�Ձc\����O\\\�rCW)y�\�J���B�GRj\�Z\'\n8\"��}�\0�q֥\�v(M\n��q\�\'�j��\�P\�_Z�\�G��\�8�6\�~a\�ڕ\�\�]\�@�y���\�pGOZ(��|y��l>\�\� ��@��>(���fK�i9\�\��\�\0IC��*x˱\�P�u��swfgik�2�\"x��@덦�-�(Z�\0i/����?�4(<\�Tn�Q֫J�\����a5.�����l\n����\�\r?�^����\\m�⼩s�\\�Z\�\n\���G���O�)��V�~1\�%Ee��\�8���\�Gz7h\�As܏�t�V-}\�\�\�\��\0��\Z\�C\��\0N_�\�\�\�^+�\�&��ޗ*��\���`�T琴\����0m�ԁ\�My&\�GZPO�>T=h�E\�E\�͒��\�w�V�^1ѥV?l@Td��+Ń\���r �\���K����\�)��Cќ~�\�\�0S?ʼ��#��,}h\�As\�\��^�p��Q�\�\�;O\�Zq\\C:��Tun�X\�\�e\�#�z]\�r:ЫK�ϡi3^5c\�\�r\��_��\0�C~�kj���@�\�݈�\�f�#\�\�y�5\�\�\\\��\�\�0��\�9$�oJ��Ì\�a\Z�\0�\�#\��4��\r�tG����Y�^/\�n%-�J\�#~��;�X�TR]�	\�,ѣ�3ג�\�̤�\�#1\�X\�\Zfv\�#�0\�Nh\��X]^��m��\�\0�\�8����I��꼑�g�y�p3�)�\�ڭ��滀.z��\���N���TO�\�*\�\�u�e�\�D\�\���\�d{�/\�b 4\�眅Ȩ�Y\�\�\�u��4���s��׍�\�+d)5<�\n�M\���=_����?x�U]C\�L���f�7�\�\�\�\�\�\��H\�(��GR(�Y�x\��\0T�\�-FFBNz\�$��\�\�\�,\�R��;��A��\�Օ8=j\�d}\�JB{mgQӮ�{k�!\�\�q늵�u�ұ��s�	\rӜ�Y��ܜӣ��,8�Ҹ%}�`\����˻�y�\r�950ԯ\�P��@p��\�UJ��QFőps\�JW+�\Z\�\�\�A�sӝǜS$y%�\�V,[�I\�N��1��RFC`�\'�t)�q�Tt�Z\����j\�[�\�0\�?J�\�`(⋋����7#��=�\�+\�S\�<T\�*�N\�mn1H�\�VI�c\�{S��h�in\'(3��e�F=i\�VW#[}��\�7�J�#\�[�4�1\�)F(�\nB�I$�(�l\�\�jd�<Ny�v\��D5�\r�8Zr@3�~t\�\�f��\�#9\�#0�/��\\ƙ\�Cu�#�W\�P!�c��\�V>\�*.Ց�\�jD�\�)�pH \�@K%Ē1y$.ǹ95\�>񦘈\�Ңh��Ҁ�	�c\'\�i�r�qץ68�EH=*��\n�9\"��r�D����c�X�g v���P\0G\'�q\n6�=�kdg�\�<g�ޚB�4\�oLd\��H\�\�Q�\�\�O�dc \�)�7�\�(��[���\�\�.�6)O\�i%;H\�=\�\�i�ƣr�\�c�;ЎU�f�΍��h�@�p1�\�)|\�5\�U�rj8`�ib˅l�\\\�t�\�dF��\�52+\�v@�w?\'�g\�\�W\�W��_��#rG\�P��\�&s��\�Y$�*\�ϩ�M�r,x u�PC�(ǎ���l\�W\'�1\"h�\�OZ,�c�\�bI�\�\rX�\Z\�6��{U8\�\�p}x�\�L��\�\�д��G^@�>{\�2T�*��M�;T%�nz�\\�r\�\�1s�\�;SE̍�9\�z�\�֜c\�\�����+�9\�w��p��\�	5U*\�I\�\�NN|�E!��\��\�\��QJ���\�\�\�\�\�Ԩܯ��������t�\���t\�I\Z����\�\Z\�FdNe \0B1\�\�\�52x���q���y��\�\�Z��+o�0\�\�u�\"\��Q/\�\�\�\�f�=\�&�w1�*\�`\�sp\�\�\��\0N�z���\0z��7Ry��gғ]\��V���fǩz�g\�6\��xy��\�g5[\n\�M&k\�G�t\��k�\0}\��\0\��zK�\0}\�cϨ\�\��\0\�\n\��\0�/��G�!z_�%�\0�\�\�<\����^�<�\�9?\�w�!�O����41\�D�3^��\0v���/�\0}�?\�\�?\�\�f�1\�\�A5\���i�\�\��٥�\0�GH\�m�\0��,Ǜx4(I��uz��i\n8�\�&3�H�\�\�mrd\\\�̠c�\rK�Z\"�I\�\�6�5iJ�\�\�06G��m\�pKVoS[ز�nP\�\�Z�7��`�:S�\��\�\�1I��ew\�\�J@\�OSҘ��/�\�zd���\�\�֐&;nzc$��t\�pH\'ҡy\�*rE1ea��\�(�\�=�ܹs\�\�92\�A8�\\x\�;�Y�\�F�\\LC+\��s\�R�E�9\�3LIp�v4�\�3�~�\�]�p�\�9\�\�M�|\\�\�\�0qS+�\�\�ҝ�\�\\2\r�q�\�L3ǒ���Ug�\0\0A$SlbI\�\�E���.0N\�I%\� �f��쪏^�Ɠq#\'\0R\Z�}��l�;!c���qUa�Ź�F*��-Fy����b\�}�\0Ju���ݔ\�h\��m\�⬉\Z*\�q�Jv���sx����\�\�	]ã\0v\�d\�\�,�x���%\�hQ\�.\�\�ڋ\r\����\�\����\�\�E\�ʂc\�#\�;U&$8\�ځ6X��\�})�N\nj���zS\��\�#۵��h y\�\�q�\�:b�|ӷ\�\n�;	U�\0��)�$�E穧	��zu�Im\�\�\0�V\�U���\�1��`\�:\�\�Oc�1!<՚�.9\�\rX�.-2\�}\r&	\�Z 2�ȩ��j��\��uڌpn��N��Xp{\�U\��\�\'i\��\�\�ь��C�4c%C.\0\n;U�%�OM�(\�i�皲?/0h���it1.\�w\�$��:�@\'��O�����\�I��G\�@3UQ�\�\0%�\�s��\�F��\'$�1A7\Z[�G�HX2�S��v���PHt<c҂��l����*\��\�\�\'�3����)\0\nٶHJURU�23I�jf\�:�\�<�L��c�\�lH��Pb]�\�J�Qj�1���\���\�%\0�g4��\��N�R\��.\�v\��Z����v4\�H~A�n�\�\�wV�!\�:��\�L�\�\"[�SR=��4{T��h\�o!M*�g�s�\�Qϭg�Y\�rs׎)\�E\�3\�*10|g��������	㞕e\�\�\��3�\ZԬ�as��5�*�\�֣q\�N\�_+��Av�d@��\�\�i�֣���s�Ғ8�B�X\n�ly\�H\'��M��~bGè\�=+9�1�\�CZ��\�T�\�I8\0P	����F`=J }��m�\�W\�\��\�\�5U�\0h6i.�9\� \nv\�۹�((�s�c�4\�B�[�������\�g�>�;�+�66�\�&2���Fy���ʄ�>��fِצh�\�\�l\�����!�ls\�E$�q�g��l֑\�?�\�L��h�C�V\0\�T�o�\�6�W#ia\�\�N�;9cvT�9r\�LV\�X\��8\'�+mon�[n��+c޼\�\�Z\�\�UI�\�\��\Z�{oYN��M�GCҷ�H\�̥j⎝j�j�*�7)��V:\�H\�o�6;?:Ӛ$ٖ\�\��m�\�/�0=+�ӯ��\�����\�}k���� �\�\�\�0pzq\\��%7�4(�.e=k:��H\�\�[X\��I\�I�\�\�h\�\"I�i\�Ӄ��T\�in�8\�v�s]f�!\�$�ZF]������4hqF>�Zo`V��1��4\�\�\�\�\r3���\�4�g�)8�>\�\0\�\�AA��\�\�Q��o<\ZB�ޏ0�\�y�(�0�£{HX\�ę�\0tT\�cI���R��N�o�o���G��n�\�1W�Q�\�E�jP\Z-��d\�1�\r=�\�/\�Mi��vs��\�.̦�\�\��\�\�4�úz�\"��+R��\�~r��3N���[q���\'��ə�%]݃p+�ϵ(oj9P]�\��NL\�@�aQ\�Ė2\�I�\�\��\0f�\�O+ǵ�9�\�\'��\�~b{d�{x>Č	%�WI�{Qǥ�9�̷�����ܒ*�M�ˇ��\�p���_J9s3���p�EQ\�	&�x%�I��$t\�ƻL�3J��֎D\�\���$d}�3\�a\�i����J�I?ų�]\�եھ��H�;<�<�D�5�\���|�ui<-|\�\�5��`��}k��\�֓\�\0}\�=�C�G|ze..\�Bq¦1�JV�5\�ۺ\�\'�\�\�s]ߗ�J<�\�G��s����Ļ|�\�$�\�5�	:�efM\�\�{�+\�T�.\���C�G��\�\�!�,	�Q�\�\'�5\��\0W\"\��\0k�k\�LTy~�{8���p�Ԕ`K\�H|���\�E�zrk\�\�gғg�\�!\�\�<ߑ��`��֔xOP@\"89\�סl\�M����qh\�;>\�\�FX�\���2�~�\�\�ce\�\�\rw[8\�G�G�����?N\�uK#���B\��}&\�\�\�ze�;�s�5\��cҗ\��>\��\�H\�?��>�\�E�Ⱖ��L\�\��O��\�>)<��j�P�V\�6O\n_\�\�FB�\Z�<58�XJ����\��\�!\�Ha�P\�&\n�<\�Q\�4Qs.;?$�T�h\�\0\Z	Tv%5\��\�K\��\n^\�w�g\�K���y�SPM�\"\\��#ע��\�\�SY\�p�K�x\�s�\�t|\��\�G�\�k\Z�.y�Յ�D6�`���\��wN#�<\�\�\�@����&\�<�����G\Z.rJ��L�iZH\�i�����v\�v\�ٓ4\�~̹?Z=�\�\�v8ۋ�_�Ʌ#�\�Uʸ�=�7&�\�Ѭ\�\�m\�v\�f�\��<x�\0pQ\�<\�\�y{up\�z1rqܚ��\�E#<�^�s�Y\���6\�UEV>��n%��\�A#ڗ�h=�9\"�]\�\�\0\�\"��D�A\"H\'�5\�\�\���\���\�?\r\�g�;�9\�1K\�\�~\�&#[<�1:��#�	шI#lu���]\�0-w\�\�9�\�\��1\�#\�O\�K�{Dr�d�PNPw$����m���F���͑��\n腌8\�\"�\�\�-dB��G��p���\�,��\'`�9n�tI\�\�\�\�P\��c�v�h�:�BPJkh\�j\�B����)��8X짘�0�\�WNvB�Fk��A/ߴs݈9�Ǥ4LX<X=����s\�R�;��io�\��H=)�\�ɼ.X(\�J���M=߂\��\0\�4\�`LX\�[�^)rO���\�\�c�d�\�j(��\�\�\r�\�կ\�,\�\\E�y\�\�P���x\�sX˙�#ID7j9�T�m\�ς2I\�ZiF\�v�\\\n�6^2\��\�ҥ��y2�\\2�Fr{\�Q��-wg�\�֊�!��\�oˬ�\��S�R\r:\�DFQ\�q<~5FY��֦�w�\nde_Qڴ�����v��w0\�\�\�j�Žݳ�<Ez��\�j\�4\�,ْ,���Oֽ�㺵\�\Z��\n\�SD�X�\�y.\��\�/�P2k\�4\��#<L�9��\�������Y\�ѕ\��\�\�4\�I�U�\���֑��Ci�\�C�\�w�?,GJ\����\�\�H$L\�8\�kg\�7��K\�� \�&�y\�I�\�YT�݊�5�n�M�\�s\�j\�\�\�Z\�1����Pt~\�\�\�\�a��\�x�]�\0�t�-G���Uy\�\�F{\�N�\�R\�\�mb�;H�S�\n\�S�8\�(�A ܬ\�2)ܓ\�u\"\�>��sڤ���\�1\r\�)69�ZM��\07m&\�~=)Á\�4\0���7hϵ<�ZC�\�\��i\�}h�\�ځ�\�F\�j\\Q��@\r\�h4m�\�\0f�g�(�<Q�KE1H�&��\0Nz�3�9\�J\�3��\0B2jarW�iX�f�\�0\�\r\��ޜr3�y\�Q4a�2�8 Sv~�\0\�O\�He��\�I\�d\��\�\09棖@��>�\�\�V�d˜sF�\0�j�W��\�N2\rYQ��M15a�a\�O8p*\'gU;W&�g��D�p�\�S\�3\�\�#�D��\�sLD�b��\\�u��?$�\�yl1�@�\�O\�S�Z�\�޴�&\�2�?xQ�z��clf��\�zY�\�\�.��U\\8\�Կ?���,{R>�T�tj	�s�\�`\'\�{�\�AO�j\0�\�,���Ɍ_\���\��?� ���w�q�b\��?�!A\��ӷ�ړ&�\�JB�t�ZB}\�2�t4\�O����W��� \�\������_\�\�6��tX�=��`��\�\�\�}i�\�?��\0�a��7a�\0&��?�!{�ʀ!(G�!ަ;�*���\�2���)S����\�x,y$��vz\n6{S��=\n\�\�ދ�\�aOjM�\�7\0v��E!\�\�1Ld\���ji\'=(�%;dzTr��:��\�\�#�8�Y�!YF\�\�sS\"ѕq�l\�Q\���sr�C$�p[ֺ\�\�i�M\�\�\�G&�k)&@\�>�\�5&tE��\�i%H\�\"�\�\Z5\nrH\���\�,�\'ݨ_X#&G�u��*\�5�\"�$�+�m\n\�\�(\��Eg\�r��h\�Đ�1�)��iw\�9>K\���\�]���}\�S�\�Q\��5\�\�.fr�\�hP�#b\���W�iz�\�Í\�6w�	�\�\�!DQ�\�p+>\�P��)��	v��6t�LO\�=\�x\�0Q�^�,�e��V\"�]R\�܇׌\rÊ��)��G\�H�9+\����\�MjK��\����p�D��\�\�ֹ\�\�7>��y�:\�\�2��ԃ���k�W��wy�[��i�\����åvZT7r\�ޢ_\�\�\��ͅ�+����\�\�o<��[�y{�2Myt]W��\����@\�\�-�Z\�XC��\�Tw�[C+[#N1#�\�\�\�i�1�:輊�P2O�Һ}+Z�U�e�ܥ��K��\'}\�h\�\���(\��A@\�GA\�ZؑNA\�sI�OJ0\�s�C\��P!s�;�\�d�����\0<�\0��\r�\��(Jm�	㠠i���\'�7{P���sN\'�� #\�m\�8�@�b��\�q@4n)\�\�! �J\0q�\�Hr)6�\�w4ҙ\�\�\���j�vT��\�r)ι\\g5\�1c<�ց�fa倜�>\�\�1\r\�MWA\�2���\�\�G+Iܱޤ�9\�;~����n\�y�\\\Z�X�q\�rE20\�M*I�z�\�\�kB�G�Y�pkf)�^\�8&���<�\�/?�^��\�+\�\�)G@�\�g\�eXg�\�U��t\�8-\�OsSH���\�n �^\�D*-\�u\�Y8\��\��ؑ���A�\�OL\�v�n4�\�g\�\�NE\�j\�;o\�r�d�U\�m\�\'�\�V䒋\�\�\�G6�X\�7~�n\�j8\�H��\���޴ v�y��p\�7\�4u8\��٣�OҚ\0\�\�h\�Ҁ.)0�\�ҍ��]��\0L(\�( �)vc�!{\�\0�1\��ZԻN~�\0�1���/����6�u\�h\0h�\�8��\�:ӰO�\0����d�L�dqF\�i\�6x\�G\�@�ԻR)�s���`v\�@\n\\Ѵ�\�c�?�H\�@�\��S���B�\�4�Ő(�\\p�(ڿ\�Z~\���&�N1@�_A�S/\�S\�\�ZC�\�4T{��%3�9Z��l�}����\'��D@+��9��mY\�O\\�Es��r)c\�L�PqP\�i�a�\�g9\�\�~d,�	�\�\�\�Qd\�8\��(Ǧ)\��FqTA�@:\�\�*�pJ�ث\��W\'�\�sU.\��\�\�ec��\�*\'�Qܬ�\�ߘu\�P\�ޕ_C�a�a�N\0�ql��v\�\�Ұ�m���9�Pt��ն�\�@>Ƣk9�\�\�\Z4\Z!\�\��\�\�E8�����R�Gv7o\��4m�S��:\\S��c/\\��t��e8�#N�$�t�9\�\�]���\�\�\0�\�8\�ڼ\�BH\�$\���z\�\�i��<Т�L]`�=)�Y�\�\�wl�\�Cm\�\�5;{�GG�Fع��5�\�k\�V\�lĨw,�\�}�.\�p�%9����aȬ4�r[@�\�v�\�\�ӌT\'(�0G$TܢIp3ZQ�\�@�^k-C�p\�\�O~&̀6O\n;\����\�$\nc�\"#���D]F\�X�Ao܅\�Y>хġ\�T�G�s�뾍$	\Z�E\�\0��*}Y��^\�\�\�qm\�\�\�3u&��iF>�\�p;\�BV if\0�\�#\�ҕ�TK(�@\0�N#���_�8���_\\s���}�8=�hadr:\�\�\�5Y[~\�; �Mq\�8�s\�\�A\n6\�\'�\�(7��\�t�$�\�I��=\�\0.G��$z��$c�\�֌w�eO^\r\'��ǩ�w���pq\�\�\0\�\�/^�\�P9��\0�:�\�!\�^\����R�\�ǭ\0�A#9\���h\ZN�1��£g�|�\������T\�+Ϩ�hs\�D\�nGqU.%\n�N\�?\n�\�e1\�?�!To�R��U��\�-�-IѷN��A-�)-ǘd�Nw�\�TJ��\',	\�\�k:\�e\Z1�a�)\\�>���Q�\�\�\�4+.����+�\�eYrw��\���8f��.\\H\�E\�a��5\�b\�y`MX�V#?.༞85Jhx\�\r���\�5nD<�@�\�ݍ\�I0htxɑ\�\r� w �U�S�\�c\�ޝ�t�R�0O�S�\r4�����`�5�\�\�]�\�I9u?ҳ�u	b�FpG�Aqw,M�?1�u\"�Įn�>UF\�f�s���\��+*�?�O�v5l��r+�\�\�xc_18��\�	�?\�[bnN\�\�WT%tc%��b\�E&_q\�A4Χ�Fr)�il�\�Ҫ\�%�m?\�뚜�\0�T���#o1q�\�f�{�����z\�\�\�\"�I�ǭ.\��\�x�>�\0��K,؈�\�G`i�\�\�b\����M �2s\�UF�#��۸�Ԁl#-\�֕ʱ>\���#?\�\�󤹹h6�\�\�\�&��\�|\�\�c��S��ݦh\�,�!JҜ��*\�\�P�%?3�G8\�Z%��\0\�\�+e,�^\�\� \�o����\�d�5\n\�\�����S�r�Bڢ\�\�\�G\\\�c�ؤ����\�\'\�\��\�\�ڥ\�\�s�P\��\0\�ds��B\0\���u搀3�M\�G<}h��\0Rsޙ)\�gӚ~r*�ĠC��\�40H�\�b�\�\�*\�,B�\�g\\0k\\d��́�$��I�օ\���SU㑄�q��i�˒\�\�lC��x☒.g�ߝ0�ߍ!|s��\�m\��\r\0%ôhe\\F\�z�q\�Ӧ`\�\�\�\�CPmʐ��Z�\�H�Fd���\�\�)\�<�H)���\�֡�G6��\��\�Y�\�>C��s\�8���\�	��yoKb�\�I辵����G8\�\�mF�\�\�\�\���WGo� 庒M:.\�L��G\�\�zU-F���b�N9���\�\"�^�m\�F7���zֳ\�\�nAsr%\�\�P\�X\0\��U\�.\�˒8# �Xr\��\�\�V\r\�<f�l$Q�$c��9\�sF���yl�\�E�\�w�6\�V\�\��#�T�>[\�@�\�Dq�A�ESܴ4\�\��Ѱ�hO\�?�\�4��(��@	��\0}*)s��\0��\��\�O�\��\�Ƕ:p�\�VdW�Mֲ/<�\��H�\��\�C�\0y�ra�&\�W�34w�\��\�?�eP��Ǉd�O��\�O�:0�иf�@\�\\��-���\\���\�\�&�\�!;%ᛧ>��R�@\��sǥd�\�ij:�ǘѓ�Î;Ӧ�,~q�߀j��WqR��bcw\�G����3��iB@Ux��\�5��6�{mn�x��\�x2�OI�k\�Ug_�+��e�w#nS\��5\��KM���mw-�5#<ׯ\�B\�\�q�\�\\�F1]e\�\�j\�\�\�Q\�YX7�\rH\�#9�\�\�	��\�[��df�\\�pA\�\���<\�1�6qϽW2�ȣ���\�Hj\�S%���\0:s̲\�Nq\�����yu.ʹ ܿ�&�#H\�n���J��*\�MHR s\�zSق�9\�\�T\�lܔ)�:ԲK\��Ҫ\�ص�\�\�����\rGm����\nRB\�2�\��]�!n=&rqީI�\�\�1\�[&;y��\0*��)\�c�pc�\��)sǸr\�\�o�\'�9X��\�\�\�=!~\�\\9\�x�f�?�,\�~\�\�\���(\�rH\�G=�w4�Fŷ�B�\�`I\'#|�?!Q^���vcK\� �l\�q�\�PA(N3�\�$�֦O\�\r��\0�	��x\�Xc�$*?وQ\�P\�?3\��*�>��\��%��\�2��Zt\�c�\�Q�Ҫ��5wvV\�\'<�\r�^\�\�~\��!%\�*�\�~��␐�����\�ם\rF�C���?Y\r0\�\\�畾�M/h>Dzc�鸝��$qY\�ed�Cl܍�\�ȯ?gc��\��&��v�\�Iͱ��w�\r�6\�\�\����\�Lۈ�3s\0鹌��s\\	\n	\�S\�@\�is2�;7���\�m\�\�ä�#ޤmGO�P\�\�[q\�9��\nTa�Ҳ��{\n9�Y\�\�oۤ�\��\�7�$��j�\� \����\'?7�W�I��v��;HsB�Bi3��\�\�\'�/`o�\�Pz㊥.�a�,7�\�\�\��ߊ\�\"\0�\�zR��Km�C~[\�i\�y%����\�+�ʲ\�\�&�\"�\�(9���\�T��}�v��Om\�t�[C{�>�Tc��~\�\�Z}�\�f>�#es\\$ED�c�j\�\0��M�4�\�Oi.F\�\�;���\��H���K|��ۧ~\�\�\�\0�↌|�s��)\n\�;8|C�ơM\�;W����I,|\�\�{\\`|�{v�9�ᾔ\�\\�㡥\�\�\�\�/\�ѩ-�=\�s�S�]ӟ\�! ��+�h���3J���|�,N\�\�V��x\�j6\�\�[7�M��b\�	��\��t\�u�\�H\�\��\���;#��\�aܭosn\�q*��\0Z�qtfC�$\�OU�s�똒\�vp:\n�-�Ï\�泜\\�\�+#�\�\��m;\����\�֚\�C�\�ٙ��t�=\�HGj����\�Ҍ]\�\�MX��;)a�/9\'�֕L�\�דF��B�\�3Ú�\�r�l��i\rt�W\�\�٣\�Ȟ<���9n�9Uf݌b�\�\��� )p?\�f�u�Tt��\��G��f���\�lI\�h\�\�`\��O\�^`<I�#��I�����\�\�f2]����\0�\�\�^\�\��\�*�w\�T��]��u\"�E񎮽Z\�1R\�c|\�7\�ڶ9��c��\�CT\�\�\�\�G�\�t<��\�\�(�Ex\�5ş�3,c��N\�\"�\�\�\�\�k\�/���T���A�|\Z|R�b\��\�o¹��J�M\�d��j��,�%�\�,�\0#Oڡ{3�N\0�̩1c�V\"x�\��\���ч���V\�\�\Z�ղ1�)�\�\�\"�,�}:J��ϭ\�)2�ݒj�\�	q.0dS�i��u\�\�d\�~3�(���W���v\�f��D��\�k\'U��q\��\�z\Z\�}>�K3�\��\�t��_E��\0[���\�ɨ�5(\�1i�6��\�\�$�E\�\�$��\�H�i�\�`��&��F5nv@\�o$\�}_\�\�v]%��\�i.��jtd�\�Ukc� �8������\�\����\��nx�/1D�( �\�\�]nq\�\�\�`�\0e\�kq!b�zU{�\\��(�.��&�\�\�(	��A�v==ꁎA\\č��\�1��9M%\�1�\�u\�c	t\���kL ����g\�&\�U+��b�a�<~�[���G�����S�jg\��\��\n�/go\�\��\��\��\"�n\��\0=?�\�(&ү�\0����j	#��7��\�$q\�X��\�WE\0\�3���Q�\�UR3*2�K��\�\�u%x�א\�1�:\�\��F&?νr��m��2{�\r\�焯\�s�\�dc���S+���\�\\`<r8I\���rrHC���Q�\�|}���\�ۣE)8?C�\�|E\�4B�C2\\\�\�\�J}v5�+х�vZtg�:��\Z;k9%F\�Ux\�֭\�\�[�\�\�S\�[��}\��\0|�h�.�\�*��o�d�\�(�}�YO#\�]��\�\r\"A�zݶz�]�g�\�\"�\���O:9\��\�tE\n���|�\�GO\�\Z+�h/-g|\�\�u�ދ��K\�\�2�y^0\�\�\�Z\�]/\�:%��Myn�\�F~n:dV[�\�\�E\�V\�\�7�\�c�洋\�D8\�\�f\�J�\�t�?�\�ac|��8�W�\\x�Z�}�=\"\�T%�\�\�-\�\�\��94\�F5�Ik�KXv\�uo@2*����S�\��F�Y�*�\�\�S\�\�Sm f�\�Du��(\�%�diw!�P�Ω��c��m?�1�e\'�\0W9�I��\�FAҖ�w7d�~�I1EmNxL�\0:��)\�fo��8�/��Ꮽ5�\r��\�\�bmF�}\�[ۆ>�\Z�_t�{�>懑v�\�8�	\�\�\�\�ҋ\�x\nXm\�O\n9�^88�\�\�x\0g��\"\�A�i�@��\�G\�J�MQXa[<��;\Z �n�\"�\����H\�6,���%�rH�OƋ���H�����V+=\����Ӕ]>Qs\�ҸX\�ނ1�\��c3�pk,�\�H2�\0��\���=\�[\�\"��蛹�Qp�}n\�ߜ�ʟ����3M�\rny.���\�mS�\�\����Mi�1��J\0Jw�&\�<획_Z׿�\�mGO\�.c�H�\�\�=�x5��\\�%�\0M\�g\0(��BA?�\ZW�\�&\�~^=\��\�b)��Z\��\�\�_����px��:�=g�\�ti�mߘ��o2\�\�=�q�Q�YD��lĂ�i��&�\�Sǥuő��Ia\�--\�q�hs\�:t��I\�8\�ܲŦ���o�Iާ\�q�JC�{\�\�\��\0㦞/~P0I욿}�Oq�\�6�Y�,\�׏z�\�{�ͻ��]Wʌ)#\�h�6\�3L��d\�?,dҼ\�\n\�t/��4�\�\�:K2\�EK����\�0)�dHx>�j\Z�x\")y��jE�\�[i\�#�Fy�\���Y$�ټ�v�\r\�Z���]\�3=켍�>�\�P=cq(��\�\�#oJ�k%\�╵����QE��R�\�Ƹ\�n$<2\�oF\��֕���\�\�<��JN���=�\Z��5MMO\��\��y\r�#Zk7��|\�\�\���e\�\�[E\��\���\�P\�\�?<\��\\���Y{c\�v�\�40\�\�\�&~\�7#���77���PO@S�tSx�V�VHv���`�2}�A&��^O�\�\�TdYLA����hb��\�ʓ\�\�\Z��K,nTu!ЍR\�CcP�8/:/�צq]~�goqbȳ$`\�˛\�dn���\Z���\�W%��*i�Q\r\��W�i���inl�i\�\��Q\�P�\�N��;�0U�\"H\�ݠ5�S\03��\��1ֺ�f{[�v:\\!a\�2:�\��\�Y\�w\�Oih��\�S�6@\�s\�\�F�d���mR��Ǧk���\�J*\\[i@H�\0x\�G�#���ójWr~\�K@\�l���\�\0zѨX\�ڴű�\Z��\�\��\�M\�\�<�%\�E�n�k0#�\���\�i<=�]�#Os�,�]\�\�ր�ϋ��\�>\�A�Z\�\�����[�y`F�R:q�ɨ\����d�w�|�%ʶO��\�,s^tl\�Kb�|�9~}뢃Ú�n/.-�]\�^E\'�㚖���T~G��Ʊ\�7$����\�׭ �\�$��w\'OZp�\\�c�5a�3\�\���o*�ʻ8P\�£�ú�Ҵh���ۆ\�=�;��@���jIPy�1ڬ/��u��@c\�H�����\��G��Q*D��q�\�S\�\�E\�b\'�sӵG\�s��\�J\�->i��T\�\r\���{ns5�\�M\�Ea\�-�ZI-\�J8��\�c\��\�Xv*E\'ۉ�|�\�F�I\�bQ\�*U�Q����1\n^�9v\�V#�E#�Դ�d�\�!Ǘyp���W \�uĈ\�n\�Foϴ��\�Y\�t�\���<��\"\�9�\�&�JL臊�8�޶�\�?�I��o��1�\�J\�EsF\�5\�<ԉy8\�4�P��t\�\�kVlIi0>��T��\�\��eFc�^>��sBx��q*\�\��\"c\�h\��եݩ\rwns\�X��q��K\�h���S�W#\\���$��H�uaKٍT= f^Ux犘O\�U�hu����&\��\0\��t#&O�\�\�\�\Zi�\0j/�v�\��d?��㣩�)���\�~$QK\�M\�Ɗy���\��.\n���\nt�Uձ�VT�\�\�@�M�\Z\�y���&)�����VU\�[��lXcl�y�vH�{����o��#j��-�\�+�h�\�\�|��\�	u�H\�P��\�j�\�\�K�.\�%��\�	~�\nh�Q\�\�N1ǭ$\�2@2�s�ڇ�<TQ��z4I6n$���j��\�+K\�JZ�\�/n..\'�a�\�|/��*���BV�\�pb��\�L\�H�\��C��|\�2H�\0y6��)򬹑|�\�e���f�$�ji���\��\0�v\�G���4�\������ZM/��\��4�;jJ\�2�v<�5ґ\�jض\�`O�\���M�5lϦ\�\�q\��Ԑ�Y���\�:ԅ�c� \Z\��^�\�\'\�\n㩅��u�k�0���\'ӛiO��́��2??\�\�(c��\���\�\�\�i_���\�R)\�\��d�i�Z\��4s)�-�\�Uq\�U\�SL\��\�/�#\�~f\�\�\�ѿƤ�_���\�X\��\�qK�|�o��U%#\�*5�y\�\�޻�mCG��$�`�\0tZU��\�j\�<\�a��4�8[\�N\�AN�N��|\"�\�-w�\0\��8C\�LYSO�4�\�\�c��\0B�\0\�\�q\�\�#�CO4��J��,eCdd�\�J|C����ٲ\����h]ɾ�U\'��\��9g��8َ\�ȴ�k��*�cװ�\�[k�r�QVf�\�OQ�\�I�<C`edKԐ�#�<W�����`\�0�of�b\�b#m2�\�����,�pA\'ך\�c׭��\0\�\�v\�ܖ\�\0>�q\�ִ!�V�<E����pG\�S��Uh#�63Ă6\�pT	�\�\��\�\�B��U\�\�\�G�M&=��Gw\�i#͞�\�N9E�\�\0��O\��\�E�\�L��A�\�-�iɡL\���\�7]�fO\�]|>-\�\�)��C.9d_����\��H���6wBX�\�M��\0�i�QZG!����v���u�0O\�\�Kg�Gr\�񑌓�\�\�A/�#�\�d;h��\�\�ך��\r�]1\�\��?�\�aiX\�\�D	s�^2�\�H`q�U�\�\�?\�\�,�\�\�\0=kg��,7A\�,��ŖL�a\�fR;�5#�r\�\�\��Ș5�Y	Gߚ��u�ܭ%�2�@�8LsW�tя3Q��E�\0\n��\��?o�,:7ٔ!MN\"p��t;\�	�\�?�\0��ԉ\�\�\�dE\�Yq\�\�?�ғ\�zt�\�+���-n1�ʣ>(�V�9N?\�~Ts@9$As�!\�W_ ��T\�\��΄�\�.\�V\�\�\\�cWq\�\�\�\�\�-ʪ\�36;s\�\�O\�D\\�+g\��^�<\�i�b�\\����\0:��K����\��\nO�J4�w&�:\�w�\"�i\�\0\�!�B\�d�\�8�\rH�4N�$I\�~P7�\�:\�\��F��6�\�q\�+m�\�P\�x�;�j8�$o#\"\�\"�F��\�ޗ<G\�!�\�A�W��R�\\k��	���Y0K<�<18\�=\�t\Z��c��k \0��\n\�{\���k\�=.2^\�2HϺ0c$l�*���\�!�\�q�V�N\�6\�\�~X整g\�\�\��LF?��C\��)MC9\���b��/\�ٛ:�s\�y-�9\�.I�E\�1q/ʀ\��S�KB�!\�m��a�1\�V�\�&\�$7\�\�)����\�\�5\�\��jĜU��|\�\�\���\�h5}K3h6\�([)?\�rN\�׊\"\� �\�5R=p\�ke�Ga5�wQϵrD�Q�@�\�?\ZΗžx\���\�\�ݘ��\0J=�z�$�Ũ\�D�dE\�HH\\}kb\�U��EF�\�Vl�\0�=���\�zL\n\��w���T�o�\�r\�p\�l\0�\�V�\���K�Q.�gf;r~n>�%��\�8d3�\r�O�g,0}�\�Oh1β�\�u<�\�?\nW�,\��ֈ݀�8�\'\�\�k�\�DЯcq�\�y2!\�s�g\��i�xh�/ݳ>\�+D<��\�r\�z,�n�P#vQ\�\�\��H\'˽�r9\�	\'�Rӣ��\��\�\�7�\�%e\�_2\�~|\�ި\�h7�n\�\r��NǄ�\0s\�\�z��4�\�6j\�&\�\�_����\�\�ԢuQ\�c\�\�)M��h\�S<@y��\�\0�\�0qM��&�4\�Hn��pǖ\�?������\\ۅi\�v?xmm����\�#�\�Hg�!\�\0�z�\��9�Vg\\xGG��Er�bGÆ#��:�/�|7ّ�e�F6�@\�Z�\�?\r���\�$��\��-�\�U���&q\�I!\�?��x��\���\��Y\�\�\�%��\�\������J�,/�c�v8�O�*��C�c\�LM��V3�\�ӥ>\�\�6Ip\��\�H㟞,�qE\�\Z�YCqeg�{g��ݿx w\����	�_\�K]4\�81�R\��\�hA\�-E����\�t���pe���=wcڡ\��9\��\0\rKRH �f:\�4��SG�kq���)\�\�\�O\�k���^�?��\�T�\�\�K\�0�\�\�b\��&�\�͞��B���)C\�s8��\�ܪ��\�\�\�#�\�\�	����t�1�hl�\�w\\L\�\�\���Ic�m\"\�\n�pH�\�?tVg)ygj�WJ�pСl�zr*\�~���e� #\�\'F\�{\n\�\�\��Kwj��\�s(f_�S�K(\�\�s}a\"�Hi\n�\�w�kءe\�	\�ҴV�����%D\�0\�F)\��\�O�p�(��^���H�\�T\��j�u�]N\�\�P0\�A\�\��?\n�ig\�\�hM{\�0���R\�Q\�\��oV\�m�;)It�\�Y7_�Yk�,�\�\�6k\�O�l,\�`�M�26�,�G�\�i.|U<��\��\�ħ<yi��i� �ҵ�,�����ތ\�t\�f�\�D {����\�ZX&H�\�F�\0\ng�A�遃�z\�s-�o����ե1\�}��(�X\�m���\01\�V��2ɨ@������M\r\�CX\��7y!��\�\�MMc\�������&Gȇ\�) ?֚��\�t	�Hv�\�L\ZC\�A�j�l�$\�\�\Z�(?u\�\�3[#1į�E��\r\'\�O��5�O\�Ag�$\��\Z\06/i\�(��N�`�\r�8U\�.p\�z��¨_)�\�Z\�uqY�\��Dj=\�b�\Z���\�z}\�q\�RY\'\�\�=�]GGR>�*\�]B\�\�G���#\�K�F�8ۊ���ܜdf��QNF\�\�\�*)/c�\�lvlV�\�BZ�>B=\�\�\�b{���\�\�x�Cʭ\�]��qPP��\��:n��\���\�\"~�4)\Z1U94�\�\�^��_<\�\�sl��=�Kv��*�fxh��d\�\�.F:\�Im\�v\�\�x�����cp\�@H�ǎI��\����\�\�3gw�:9!�Xd���\�]�h�0TS\�$�m\�\�f�\�^�h\�c\�7�=\�,�w�E4;���t�\�2N\�\\�P\�NG�<�bf\�(��7*r��\n�4\"�>\���=ȥKy.b�s�Ğ�;�V-a�\�ڒ�e���SEܫ�El\�!\�\�\�\�\�}���dx\�0[���\�/�\0\���,�\�\�\���ڡ?\�\'>�>�g%\�\�G�e@PNMn<\�GR\���I�9\�pջ�xcV�)�KfgG!� \�\�Co\�\�R\�\�\�O\�I��\�UaRG��1\�:\��w\�\�Z�s�7��A\�Q\\-Y��\�\'��{��\�\�u�bB\�H�(\�֚h\�h�e|�~i\����\�vv!��\rq���\�+}{�\�u\�&��RC��cJ�\�\Zfm\�2XO,�\�\��\�\�K� ��Ʃ\�}�\�R���N�gPr��ǯ�B\�\��:+ǻ\�9�E6!U~ps\�\�br�\��	\".\�\0\�\�\�W8\�G�g�R*�8<�;�~\�=iI(��3�\�\��Z3�\0�\�\�U֝\ne&=�j�\�	���b��%���y(>\�pzU�d\�\�\�V��H\\\����v�\��Z<��\�\0T�Q\�;���r�J�\�2\�(N?�)\�-\�%s\�\�\n\0�Z8Դ�\\*\�h\�kcN�\�ke6\�\�l1�Ċ��\�o���-�\�>|\�\�X�*{Co\�6\�fS�\�\�_�;\�H.v� Q��>\��eEf?���\�߮�ET��b�\�\0K?��\�\�+�\�{+�AӯJ\�\�\�\�\�3M��\����T\��&\�nP{q�q֤�\�y�*ܺn�&K)���;8��?Qt����\�ҰʱǇoqT\�\�s@��,/U�6��\����_��i>\�>\�a�\�.[\�oM���\�I��\nL3\�q\�\�:���X>�~\�1W^�\"���\���\Z�\�B�Ã��#��k�Q�[	1\�-j\�ש�\�z��K�\�~\�Gl\nC˶:�J[�a�89��@9\"�H~�#�9`_7=�Ry��a�qI���\�\Z�\�#�\�Q��S�\�H�S\�`�\�\0F\��c֢�mN=jPAN�\�)d u�4���\0\">�5<�7 \�d!\�\��R1���$�\�$�\Z`$|\�\� )\�\�P\�\�# z\��\�LP\�\�����\�W���\��)ŷ\�\�&�M;Ew&\��\nh \�j\�u-�$�+&\�����q����\�!�*�f�E\�x\�i#p3D��\���	 \�Rl\�zb�GRE!�q׊\0@\�\��i\�Ƚ3Ȥyz\�,EǭCg�V$u1��\naTd�hJ���f�����t�$p:\�r0(\�\�@\"��\�I\�(\�,Nq֞<RȞ0�ֶ<%\�n7\0aT�\0*\�\�6�H�WA\��Tlc\�����v�>l(#>�!#�\�Ǿ?¡�i_�rO��F��\\~<V��\�BW��\��\���\�~�\�4\�\�>�m�dP�H:2�Ɗ@ў�8�A��y���R#n}qYW���\�9?욖\�H�uk՜\�܈r\Z\�u�)R�\�iR&5�\�\��\0\�X7\�RH\�Rļ#�a��\�X��XԖ.�\�\���<Q`��\�\�H��|�j���\�z��S\�N��\�1�CQ\�+\�W*\�sp5�1��\�T�ci�\�G�x�\�ك\�Obº�\r)�{J~��Y[>��l��ʋ\�\�s�@)E�fu>?\�׭�+\����F#\�v�\��<Յ\ZJ���\0��x�\�\�컞=䢰?iS\�W�4@}�q��\rz\�\�hs+G.�n\��@9��U�\��I2G��`4ט�y3ث�D\�~n\�j{\�\'�FSq\�<W�ɦi��\�i�Fݳɬ\�,l\�\�Km(q�2t�#\�c�pX��-�fU\�y=\�+\�N����g�Ξt\�4�8\0�\0�b�<�\��\�9\�\�\'\�\�9	:\�\�W��\0fi$\0֐}|�M\Z6�\�&\�ؠ3�ݜ�Σ�\�\n��^T�\�a^�.����\\�\�*)��cf�\��Q@f-\�	��	��424dv\�\�G��\�R�m>Q��y�F�fy�4\��4[F2\�=�kk6\�\�R%\�\�a��\0\��W�\�\0a\\w\n9���`bU[uRv\�m��h\�ngFO��|��\'�>��x��F� \�^�\�N�\"��<,\�\�S��ݬ��vh\�\�\�d\��+X.dX\�.\�\��-��rk��Ɠskp\�Q��\��o���Xs�VŎ�}-ܑI�\��Ҳ�\�ʺBe�\�\�{��H��\�\�ǵ\\cq7b�6V�1�@�����fIԜrqP\�]\�Ԥ��\�2ˁ����U�\nNc�E\�*��ᖏ>����_�� ��[w�=?J\�\�A��\�ހ\�?JI���2\�R���\�}�X\�,\�#e�\0�\�>���O\�˥i\�+n�`Dj9=q�4��\�\�<G5���Z\\\�g\r�ݴ)>c�ϩ�;\�\�5$��\�v7̌�\��y�\���R\�(\�gP3\��Ɏ�\��d\��\�\�,���Q��X�\\�{c��ĴѼ@#rO�\�v\�㺍�\��\�l~\��^\��;K(no\�{w�{7�&R��{u>\�S\�-�ԅ��H\�d�J�\�ҡ���f5�\r5\�̬Dj2��\0�x���*m$11\�]��b+\"���\�\�}�P[\�Y:��I�r��H\�h\�h\�V��\��~\��\��V���[C�\�\�I,V�˄\�!���\�(��)�+6	�\�)\��ǒ{V�Q\�ynd�W`;1\0zTB8���f��\\\Z\0ˉ\����Jtrƭ�y\�ҴV\��\�QW�\�\�:+kvVͺ�\�\0g��l��Rw��X���	#���I\�#�=j�X[\�tTHѿ�y�\�A\�\�\�t��;�\�1R�{��\�\�yi����\�4�\ZG\0�o\�\�{\�;;��\�΢\�\�(?\��k=\�e�VL����\0���\�N\�;]@ȕW�\�\'���)�\�\�W\��m5׆K�����7aQ��4�Zk-+_�L�4ӱ\�E �w\'\�g<V}��il,Z\�\�E1\�;�1\�a\�>���S\�Y\�\�vv\�瑕��~�y\�?\�[E\�I\Z�\Z�v�\�|�e�PP��\�;{\�\�\"0V�A\�c\�}LW2E\�5u��rK	]\�e�^8>\�פ@��j���ݱڮ.\�k�j:��;�\0皎Kt��\��b�}?�]�9��\�/ΪH|����\0Hc��Fq\�ڪ\�h\�kMM���Ĳ�Wh�g\��:�k�\�D\�E\�\�呃)ެQڽOW���\�E\�`��Q@\�P+\�\�ָ\�\r6�i\'��\\èƹ�7�\���d�)\�+�Y��bhp�q�\�$\��>�\0ZŒ\�Z5>n0O�֎�<\ZU���i�d<+)ᕇpE3W\�`�ʞ\�bl\�	xI\\�;��+2�q_��w��AM\Z�\�,��;(ԓ\���\�6�\Z\��\"6$v�\0{ާ���\�\�\�PoՁ9Q\�e�\�\�Zl,��4�`\�\�&3\�i��wv#6\�0��z\�	oVRO���V��\�\�\0.�\"\�g=�\�đ�����H�ӧ�)>ܥ��&\0�Q}����;}M � H<\����z\�\"\�Q������\�#�\�P%�2q�\�,�-��(F�H1\�\�Z2\�>�55��k�\�\ZFK\�b�i`\�&q��\�>����)�\�r:~��\�u�\r^��QnY\�\�2��V]�FV���|뻿�z7���Ś\�j�\�$��}}i� �u��j\�Zi)2|̹=)\\\Z<\�o�U\�s�rԆ�#;�爵�K�2\�\�\�V]\�{~�E�927_J`N��\�\�\�\��ֺ�\n�\��Uy-O�\�)\�\�M{oݠ�\�ڀ-\�un7�zSM\��\0���\�d0#�Fm��u\�\�\�G�0\�\�|�>ƪ\�o���6�\0 \�h\�]D\�\'Q�\ZF�\��\�{�T\�\�u���h\�eEQ��\�>�Ҷ$ -\�Y�T\�$Ƨ\�\�\�@т���������\Z\�\�\�M\����\�pbEw�!�\�n\����t\��j|���>���\�<��C�Dݱx3\�*P�c�{֤�\�\��\n�\�q<�\�d:+�k:\�kVa\�hUbF1Z@F[\�b8\�sH;��,��h�\�n\�?E8�\�\�-��rO?�B�����\0ZT!Nv)#��f\��ar��Eec�\�\�\�s��T��8;c\�Ҧ���yDk	,{R\�adS\�	ʃ\�R���+�O�Բ@a���\n��{R,{�\�@I8]�$Wl��\�\�\�Ґ]0\'k�z�t��\�\�c�\�*6\�\���\�q�Z5\r�r�a\��\�4-\�y�k�ơ]6v\�F?ڥ���t�Sx\�\�v}����x\�r\�H��˕�\�{�Qg\�/-�p��Pдod+�T�\�n\�#\�\�4\�\�P\�#\�HWɩ��.6�\�\�vij\Z��8WJ_���8\�t���\�\�7\�3\��=@w\�ߞs��^�ݞ�Ê�pNn	���6^F\'\�j�A�hl`*x\�*\�aW<տ�\�zd�\�\���鯧\\�$\�8��%�f\'v=�\�T\�zpH\�Ү��\0\���\�L�&K���s�{�\n⹫i�\��L�*�S!G\�UZ\�\�W\r�O�t &�0;qԷeV�\����\r�VR\�f�m�g\��\03]Ņ��al�X\�����.\�\��Y\�Z\�\"\�,Aimb�-\�\�RAi&��wn\��)��5̾j��r�H�-\��˕�k�v�f�8ػ��8\��*�fU��zaH\�\��kU�7$2\"+gp$�~�\�X7>Y�e�9@6c\�\�mI<ǒNs�~?J\��{��ִ��%�]��\��\�ϯ\�C\�\\\�6&i	.\����>��\�\�\�&�Ҽ�#>P ���0H\�Vιq-�\�:-��\Z_��ą\�9����\��y�\Z��\�o,A\�S\�9\0~U�`�\�\�%��$�����kO3�\�\�=�P��\0K��%ʬ1\��u.x\�{U�:\�]CO�-n���$8!�\�q\�*6��-KLv�[j\�.�\�=��\�J�s6;h�\�\��Yd,\�$�`W�\�VDŎDv�\�\�\�\n�(B.η?$s\�\�gчo\�։,1���!gc	w��\0<V{�{��ci.�\\rx\�Ub�\�pP��\�*\�\�\�/�\�@\0$.rޕr;k�%\�\��\n�EBǾs\�*\�e�5\�<@��L\�x\0�}�ޡ�;�h�uN�72�����ի]Q��g\�\�PB\�z��\�wD\�eP�\�8\� �\��J�\�\�G=Γx�v�\�?}Ns\�S[hwӣ��6\�q!�4Y�\�Y���d��s&��\�i�\r6ݢ_1w.\�a���#�X�\�wdb��Dxo\�<UV\�/\�9��\�p�\�\�\�[�Q«��227�\������\��\�\�ɐv0��U\���	�\�B\�?�J�eՋF\�ۂ\�ۿ�\�l��Eؙ=�F\�d��\�H �\0x��~ݪ���G͹�!x\"ll �3\��~�5j\�Y�C�Pv�.\�\0z�z��n�&�G�0\�Ƈb�ù���N\�\'ؑ��SӦ1\�A\�B\�G\�v\n;�\�ԧ���f��K�C	h�p:�\�\�\�V3<0\�$s�\�s�\�>U$~�w\�sB��u�t�\�\����\�qZ\'˩�c\�\�+\�zSi���ݻ�\�v\�#\'ؚ\�w:�\�ʜrqָ�؝Kf��f��z`�\�]\�w\�\��G$~`\�\�\�׭U9s\Zנ\�\�@T*U�1\��JIP|\�$3d����ƌ\"��x �4�T�N\�9\�:\Z\�\�9^e6��V|\r\�p{s޹\�[H�E\�[S�U���\0�J�\�{V���ؒ�\�\r��\�\�P�6�����_��U��\�\�h�.�L�/�n�>\�i\�u˅9��\�E�\�@`m>�\�\�\��\0���;j\�\����P�+�\"-\�7��ebz�ER�е\�o��&���+�\�\�ƊJ\��GӮn-n�>jd7\�z�T\�+�\�ﴯ�\\B�m�\\[� ���\0<ϸ\�?*\��\�\�Pٕ�\0}@r��F;�>\��\n�	<)�	�����\�<7�\�qʤ\�tx\"�$��w�\0���\�EP`Z\�\�u��\�,�\�\��*��\�\�\�:s��\\�wFtk��\�P�\�L�aZk�j$��&T`�\�\��\0b\�~\\��.��1�Qf+�%\�ǭ+��֢h:�<\�\�c�چ\�N��--��	\��4Y�\�?��B����t5�o�\�ܢ�VN˓�3V\"�\��q0�#\�¯\�\n,WD��\�Q����8>��\�L<�\0\�7?{\�ƹC\�\�A2R\�p=\�f��K�G��Q��և>dz.��Yx�ԮГ���`���y\\h�3F���x��E(�	0A�\�9\�v\�i�$�!\�k)ei_��<�˶Z7b��\�S^W�\�\�oκ�c��Y���,\�\�\�ҹ�⋡}�:��f�G+��ǡ�\�\�\�kJ\r\n�h�أ2#��4\�����W\�\�G�\�\�|�.�\��:\��)\�\�w���՛\����u�@\�\�P\�ר�4�\��\0\n9Z\�G\�9��\0tRM)\�~D\��\�ы\���a��\�&�m\Z�Y�\�\�x$╘]�\�\"bu��I��\�k�Pu]�\�u��m�݁x��\�4Y�\�Hʼe��w�Q��3\�\�\�\�;\�\Z4�\'x\��\0u��\�ڵ����]\�\�$r*�atn�W(W\�1O\n�\�\�\���\�˷9\�x�?\�>��\0\n��\\��@p\�\">\�\�E���ɑ�L\�u�G\�\�l��\��d\�C\�$~OV\�\�)wW>\��c9Y�Y\�Pah�Q�D\��˭W�Ţ�ˑX8\�\�)�6�g}5��\�\'8\��q����\0	\�ݱ\�-^\�\�.\�\�*|��\�V�wdV�\�/�r=y�\�x\�e�X�\�`g\"���ayt\�m���������y\�Y�\���\�\��\�՟\�	,1\��\�P�\�M\�b\�\���s4ֻ�p:c��6U`\�99Z\�H\r�q���\�\�o�N�{��\�\�kgw�\�����\Z�O\�\�\�+;\��M;i\�(\�\�h�\����٣{��+9\�\�\�(H\�6\�(c�Up]�\"�\\y�s�zQ6E�nDn2=��\�\�\�d) \�j�uߎ�A\� O��\�\�i�\�B��b�z�u�0C�J-8�\r.x�\Z�Xa(1\Z`�\�\�D8ϖ��T�)\09 zVA��\�\�\�^��e]�]��ʐe�\�s�ӿ��`\Za�w��\��\�N	|���\�J{�d�<��こ�F��]]Ggm%\���q�\�r\��\�w\�\��\�\�\�q�\�26\��+�O�~YM%\�1!��:֦�s\�Q\�>�mc�YQ�\�<qR�\�\Z%m\�G�+KUo\�\�;k�]�cNW���>����\�Ij�<~`\nd�ᏮaR\�#\�]\�Qؖݜ��j�M�{8<��K�夒S���t�V[�р��v \��1�O2\�S������M+I�\�}8=}9�άJ.22A-\�\r\r�`Z6܈��pzz�b뺌1\�bdC+ԓ\�\���-\�Be��X�\�\�\���5\�z���ƪv�Xc\�\�\�\���*[m;1\�-\�;xn\�l�7�\�\0������ԯp\�\�H�\�\�g�\�\�\�M�v�8��\��䓰�\��,\�\�S\�:7\�cx\��\����NEBNE6�\��\r]�2]\�$V\�bM\�,�\�\�\�\�H�b7����)=1�Gҳ\�\0��+��׷�b]�+�rFg^�����\0\����\�\�(̤���\�D����M�B\��\�O��\�6aN\��)R7�\0�GC��\"�\�Nk�T{|\�<\�\�\�AU4�<\��Mb\�Co��m�\�\���:\�U�,��1Ʈ^F\��煢M�z�4��.o\�P<�(ڤp\�+C\�@\�\�_�\�Y�y�\0����\0]�\�2�\�z\�V&M\�aW��G`\�Lc�P�z\�\"��^��\ZH\�u1�#���\��w\�\�\0y�)�\��Te�Z]\�rD<��RS�Y�ү�{�\Z1fP1ޯ�\n\�\��\�T\�ߚ�/u��\�6\�xoQ�7,b\�\�`�\�\�+	n\�{g�\�%6܈\�s\�sո\�\�޻k�\�V�H8vRѸPH\�s6�ΗWC�x���8\�=��\\�\"�\�~���\�\�5\�\�g(�\0#J�\0\��J϶�M#T��\�\�\�+\�\�\�g��\�Lou{���\�\�\�9ǷJ-�2���\�\�e\\R���LP�i����\0\�y���d\"BW߭nxGY��\�K�\�\�%2+�g?���i�Q�\�K#\�+\��k;A\�t�\"}�V\�ڄncgW8Ǹ\�(Q��:}�\�s�Eu�IPv�\�\�ڛ�7�d�\�S�\r;�!1\"ۍ���\0JBT+��Ai;��5�9\�\\�\�(�F�:\�*\�\�*��3�%�\�L�˄w�{\�V\�<�O�qU&}�	�\�T��b#��>�\�`ѝ\�m3M�ͮיִ\�E\n\�\��vn+\"\�S\�tD0\�\�>�\'\'��\�)2\'�ͷx��\�q\\��\0��6��v\�۰�\�!�\�{��������\�D�X�*\�ea�\�ܠ\\Fg_�?\��\0�VLW��DPL���^�v�@\�\�u���w\�m�9Q�>�SY���cڬO\Z*��d\�\'\���5Vb<�9膝\�ՙ[Ia�� \�\��\�\��U0m\�`\�o$�;��ޓ#p選\�K��b\�\0�3\��\0Z�\�\�zM\�\�\Z9O\'�\�\�\�栰|\����Z@N)��\�  \02E\0Ewm�F+�édr=\�s�ڦ�pR@$�NQ�\0�\�]&\���\��\�d����\�\�k:�Z\�\�L۴�/ Y�<mؓ�d���\�\�K��\�\\Bj7\ZU�\�o �F\�j�x\�XC\�㑞�\�tnw�\�l\����UNK�o�t�ꤩf%�\�\\P���p2:qH|W�ܨ�F�E$pɚjv%\�\�k�\�w��4\�)�El\��\ri�@�\�7��	�>�\\��-�q�Gަ��f��:E�i�ʱ۽�\�\�m\�w\�R�l�	�Q^p|k�\�\�<�x���\�4\���j�K\�s\�Z\�<ćԾPH�(�}5\��_X�կ_ΐ\�@X`��]S\�WDe̮a(ٍ�\"E�cA��D�\�Q�9=\0�\�x\�V�dc \Z�\�]=\�p�\0��\�\��#\�\���?|}\�\\t\�#�\0\�i�Edhg\�n:�\�\�A\�5��\�r�O����W���\�c�Zc\����{RE	�\�C��)�c#\�\n\�4P���\��\n�6�$\"+�#<�\�?QTỎUo��`�U�\�4c�\�(԰\�졕Mޝ�9h�O�\rl/�\�\'�ɟ�}7#\�O�[�r,�9*T\�zTkn��S(�()��\�*�6:5�c�ȸ ��ޛ\'�o�v^�����W�<\r��2�5\�i^>��\n���\�C���?\Z�̼Ĝ���\�+w��u�fl\�#�i+\r\�3Ȫ\�>\'\��/�x09�G\�ZIs90�r�8(�浅t��-F[2��.\�<�]\�\�\�FqR=��c�T\�\�]#�c.޻��UH��r̻\�#5B\�\�-y4N?�\\�H#r\�ҳ\�H\Z��\�	޿�]\�&ƫ`�=i@\�jh<u��\�\'��\�<2�y\�=*���\�\�s3,\nN#\�S\�X�\\]Z��\�wF��\��\�Z\�rܞ�7�V�\"�\��8(/�����	5\"�\�q\�G0(�:ƣ{�\�\�P\rOH�j.�hK�$8ϡ8����Fcq�n\�ҹI~\�\�^\�,$ktC�L��}犞b\�KZ^��\�3\�;\�}�#�\�\n�}��n3!v�\�X�UQ\���T\�l\�ŭ�V(W\nzc�s\�T\�/e�\�\��\�$v\�\�N\�\�\���Oz�d\Z�l�\�9����$/\�cE�Q�M\\\�U�=�z�未9#h?\��tZ]�\�\�r��\�\�S��#f#ٖ;�sL�E�Ef߰u,Ǡ�\0\�Ӝ���e�Bd`����jڣ\�#`�\�[�\n^�*�iPK\�p\�\�vl(\'\�\�V4\�b\�VrM\'ٮ6Ncf�M秠\��^h��\�k\�\��T�~\��\�C��8\��\��\\�u��\��M	�r�e�ϩ�۸\�\�ǹ�̰�څ�Gb����<3Һ�(��H\��ۈ��\�\r��\0e�\�k\�kXE��7r[\�\�d�;�z\�O�i��\�n�&��\�8�\�C�\�cr&Q�\�\�\�ڑ�\�K\�  H�z_q�ϰ���	��|�~~����\�l\�Ie���H\�\�J3�؞���eI\"�v�\�Hܲ�=\�>`8\�\�Y\�N�\\�/۵���O$����v�g�O~+�\�J���Wi\�X�wMc\�[2�bc�\�F>�\�\�ݔ?f��-\�(0O�\��\���mHm�;�\0���	޸���8\���\�)\njw\�O;��U\�\�\"��2f����ݞ�c��Q��\�L�\�ލ\�v3ڡ�\��q\� &f��uD��l\0N{�\�dg;@�\�U�*�@ �j���l$�q�eL�\0w\'�\�V3��\�^��\�\�8f)�#�C\�Ef�[{j	W�`\�\�fQ�\�\�L3\�\���\�\�t%G�:\�i��\��%+c�F\�\\\�Jo.E���׉�ə~@æ~���\�\�2(��\0�IAxɉ\��\�#\�V��PҒI�ky\�q^��z���\�,qHR2>Vg޵4���Е\�\�\�36@tr1�w���)�.O\�\��5\�\�E�ŷj\�Q\\x~\�\�\�^#��\�%�$�\rی�Y֮\�\Z\�\�#?�\�%���/[%��|�\�ަ5\�H폥Tw���\�\���05�\�#F<��y��*Rɻ\�\�\��ְ�!�\�Z\�#\�p��ʀ��o~1[��e��\�6󑌟Z�?1����v\�Њa?\�AcǱ\�\�	7c�l\�ԍ�<o#�f�\�5�R\�k���\�,rm�Y�Xz���A�h�\Z\���Y!�\"YY98\�*}B\�4�o�J��3�s���j�I�O5BrXr�;\\[ƛ�\�v�\'��K��{>C1\�ǭk	$+GPk^�\�\�\�&�yh�\�C����>�\�H�N2\�sq\�I(\�и�4�t\�D���\�Z\����_���\�\�b{T�����ñ��)n.Q���n	�Bb`3��}\rS\�T%��$}��\0tU��\�\Z�l����ʐ��=�|����\�\�q��0\r��t�+084n9>�\�9�R\��f�f㎴�\��9\�;�8��Nx\�HI|�\0��)��X`��6@\���W%\�k�/\�\�m��=�]Nrƹ\�$\�d�UM�#�eW\�4���n�ZH�\n�A�zA`vHqZ7\�=�\�\�泥�}�	S\0\�c�H����nx��\��?:0�c*1֪Yv�\n�\�)���\�lT08Ȥ}&�m�\�H\�J�2�\�\���\rR\�\�aX\����/ �\0J�e4�|rۑ�\\3G\�Nj\�\�&���a\�\����$=\�#6Q�]f\�\��\0J��Ǵb^\�5\�x�\�w�\�aL�v��W.�m\'��eN\��)�\��\�-\�,�b*��9\�j\�\��G\�\\�����\�_\"Mː}1]Pc\�vR�Q\�S\�O��I�\�\�,F\�U�I�-\�Qk\�K�Z�3��R��\�)�V:\�nm\�9�`\�\�٩̎�p��N�\�|�#g��~\�W\�`\0-�t��f�UU\�\�tΣGpV\�\�3�f\���gk0\�5\�\��\"k1\�:�,Y<�V�\"\�\��w\�\��\�֭I\n\�\�wpp0\�C�*�F\�\���(�#\�\���\�\���㟐d\�K�]�b�(OR�We�m\�\��VP\�\�$\�T�Iz\�N1��h\��\���ĭ\�J��\�6d1]Ƈkt\�I�\�Z\�\�<:\�Ѵ��\"\�u�D\�peRc�6\��-\�\�x�j�\"������-ʠi\�+BK/jB��\0~�j\�\�\�َۗV\�\�U�U\� ~Xj�\�kwl�jN)���:ok֣+x_\r\�?δ��!jl�\\\�[̓\�\0?��D�YO\�@ϥ\"�\�9�j}�\'\�ǡ\�V>6\�owy[�r���\Z�ś\\\��\�Js\"|\�O�9�+\�!�.2�\�ִ�nnl�\�\�>e �>\�r��ZKfz��Ɲr\0���\�Ly�\�\�\�b`\�H\�^��y�x�.5-2�?�\�n\�?\�V�մ\�\�C6�f\�\�\�\�G��7�D\�\�S\� ��BN	bx\�[���ta�-3w+�Wܚ\�b�ӯ\�mCX�h\"\���q\�0k�\��K\�{Dvw�4�\0�MϿ\�Wm�T�7l���b\�ᜎ��p\�*p�j\�1\�j##=Q�J<W���58�\�x\r��m\�md��U d�A\�r*�Y��\�\�g�ͱr~��|U��\�\�Џ�G���\��ն���\0֢\�,j}�\���\0�([KR�4���Ef�h\�p5k<�\0��\�\��ui�ٿ\�\�\�\�����A\�\�i�6\�&�o\�^!\�|?m\"�x$�e�So\n=[�++O�k�X&mٖ1#�\�\�V:\�\��΅t�\�Zy���\�brܟ�Z:�\Z\'�\�B\�A|�M\�\��q\�zg�\���fvr,\�z�	\�\�\�F�?,|��=�\�\\o�ui��M�FH\�;v6\�t�\Z�h�X\�^K)���\"Ul�u\�:sT�M_I���\�V��\�yp�\��=9\�*��3z�\\˹��q�8n�e�(bG\�\��u\�/P��\�v�ee��S�\�s׊\�MgKК\��7N�.�\�>l����%W�cK\�\�R\�K؋\�o\�t�\0,\�\�\�覴���\�\�.<��2�%�V]��3�i~\�\n��hB�$#h\�G\���\�T�\�\�%�H.cU\�\�\\\�ǯ##�$S5ˉ%\�dK9(�\�\�>��N[�\�N\�?kiu��,Q��&O�Wr2Q\�V��\Z{Oc\r����	�v�\�^Ond�6�G!�\0X����P:�8�5f\�\r�\�1.\�\��\0\��1�Jm�UI�+\0ډ�~�9�\�t��\�?Z\�\�-\Z^y�\�\�m\�\�\��_�zꂲ3ekF�\0��\�=W�U\�܊ε�\0��\�˟ʮ��?�5�=ə\�.	\�jM\�Z�����<1��\�{w5�)�s��JH�\�4g�\�΅���9�\�Z\0�X\����4�걕`s\�Jj�\�\0E<Rd\�jUf\�\�㱮G\\֧��[H�\���l\�\�\�b\�*��k\��\�[�K\�0\0\�J-�\n�I\�s�\�զ�\�/�����5�\�s&��\�\"vc\�\�U�Y.΃2j���v���\�ޛ\�}FW�{d�dd!�_n\��\0\���{į�j/5\�\��0ʭ� \�\�G\��]^��^\�A\�X}O �J殬��\�;m㑤��\�	\�\�v\�Z>ԡ�\�\�\�~Yp\���OR���q-ޙ�#�\�\�+p\�ֽ\�U�|ÖY\0��U\�j3\�i*\�-��u�i\�\�\�$�־��A�\�2m�m�D��\�[;\�\�\�ә\�f��\�i�[�pd{0�\Z9\�P1�C2�\�.2q�wܹ\�K���e\�%d\�����\�n@���\"�nT�\�\�z˹�[�R\��$h���9=�14.�l5V��\0yʞ\�\�-C^\�\�\�BeCSFO?�z*��x�E*yRW׵gx�R��E�*\�6\�C(˽7\�+&f�\�\�c+D��KV{���|��\�?\n�~����ڬ|A�F�L\�|�F΁��\�Ky{msip\�s	��dۍ\��\�	�X,\�sn\'K\�(�V\�\�h�gP:qU��	�80NF0Gj�1��6/�軦�ޤ�׺\�*��K�\�\�\��O�U\�\\�B\���n\�(s\�iw�\�\�\�\�n稠	I8\'4q\�DX\�\�ѻ\�@g�\�R\�t�uYd\\�j\�y4\�4��և�\�Md\�\\�\�\��eS��zuݴW�ysd�r*�\�\�Ɉ1��}\r�UmO9U�\�q\�E[Җ/\�+<b-\�5w��X�@���:\r�\�\�R=){�\�#S\�Ŵ۬%Y\"?1\�r��}W{ �c���\�\�]$\Zu�\'8\�@\�\"�j�Lw��\"ʽ8\��Q*Ot�ѝe��i�Y-��\�|\�C�r��W7\�O�r��\�F�L���O?�r�-֙#�\�\�p\n\�\�|E\"\��&6�	\��+�5�\�^\�A�x���\�:���u\�z���	! \�\�)�Εe�\�n\'nH����\�qoq�\\Hʌ�O\�\�N�aQĉA3��WiӀ@ z\�9���+��^�������2� �Ф�����\�l`��Si�S��6�UKG) vaW� �A�\��8\rD�\�\�b�9.�/�.�ʧi\�*&\�ON��l٣ʎ�\�^I�V\\g�\�\�5JI+��.\�Y��\�h��W\\\r��\�f�\�\��\"8d�sT�Z�\�H˹\n�r��Ue�*&\�\�\�\���ڽ\��\�7n\�`�d�xdR�#\�\0������\0J�\�x��p=O5�\�9�ʀm՝��.Ѧ\��`�͓GM䫂!���\�|\��\�\�\0rN	*=:\�)XM&s\�M&\nD\09,\�b��t\�K��V獣�u.��.\�O^A�^Qw+(#֫��Ȏ6H&Fe6ˏf�\0\�\�mu>\�\�ѫ��J��\�ǀT�PM\�\�\n��g_\����\�B�fNb\�\r��ҧ�m\�\�\�`1ջ�T\�:,�.DRm�\0�M�TKf��KM�ĊF*�D8��]ŌW�*8��O\Z\�O�\�E��ǈ\��ǥW�O��|�s\�(���m㔀���,veVf\�h^\r��\�ܷ�C1���\\�{�x�RK\�MI�\�\�Z\�㉐⧞#\�g\�H%#\�$q\�ZU��\�\0\\��Rk�o�����\0\�\�8t?֘\�\�C��<LG�/�\�\�\�ϋ˝�}��J.\�F\�98�~��<�1ܶ*���\�J\�\�%\�4�H>�^,9dW�֠�c\�\�%\�=�\�\�ք�!�5;tk%,	Bq���?�5�#g}2\�Q>�\�qYWN��J�W���(\�t\�\�;;��o�U���t=\�U\�Ė�\n~٤\�\01�/�\�X~zmeu�\"�>r<\�؊vc\�F���\�\�*�i�)8[�A�\rmEw\�۹崖\�E9���Տ$(���&\���\�*y_FO#[3\�F�ޣ\"I��띡��\�Yo\�&���w���݀��籯2ˀ\�[\�\�H�\��\�\�\�	\�;1�ާ�\�\��-��\�	\�D0��o�-o�z\��Ș-��.݂M�~����Ku�����95�k�U	�Ibu�\0n1M\�}I\��$�^\�-ax.,^K`~T�A\��=�Y|5x\�s$���{�\�~<\�A�{H{\�\�Mh\�\�\���x\�\�r\\1�Q��F/Ȇ\����\�Dr��T��*˜�{�\�o\Zi(\�i\n��O\�iWƚ1\���\�)�>�\�\�8\�]Nj\�\�U�듷�U\��c$g5-���X��By\�\�Sl�\�(9���Rx�\�M�o\\\�?Ɵ\�R\�\�Q,6��PN85d\��������\0\�Ա\��n|l�E�\0{p��Q\�O\"\�QG IZb�g5���u�&\�6\�J�#ñ�>[J����\�,D\�\�\��bA\0�A�ؓ�A[�t �U\�7�H\�?\�^\��23ax�3;})»m\�|hP�0}�7�}\�X\�z\�\�a\�)�(y����~(vR>Q��\�\�+�\�\�=9���v\�<c�\���;�\�ϱ��M��\��2FpOL\�+\�봷Ր8TVB�k\�$\�nf�c\��\�XW&|#�A�\�\�I\Z?\�D�\�5���p�+5b�\�l\�\�.��HH-�!�b*ޝ4V��uj$?\�z\��\0\�\'>�3]X�hH*��s��\�\�\�&��\�4\�S\��\�}8�:�\�3C^)2#e��\�`>n�\��\0פ�Ɠyar\�E,�J�IH؀~�\�c�\�Z\�[�ʠ<�\���\�,{\�g�զ��M�~C0a�1�qZ\�wZ�R��N.\�~n&���)�J��϶\r5\�H�1�\�aOJu��s\�I.���aʟ\�S\�l����򓷓U\�	2�F\�r\0\�\�W�\0m\�\�\n\�+\�z��\�;9(r�\�.\�16�N\��\�fgA��j�\Zs��J�r\�p\��¦�%�2\�ݖç#��\0|v�YY�Wd?8�$r�����+���馑.-������_;\�2L�\�\�\�H���3[�g�-\�da�P>�\�Vui\�F]�-�R�Yk��Y\�o/u�r�\�@��ZRj+N�EI�3�ܣ\�OI���W�\rQ��\�uk�N-�\�\�*\�Z1J�ɲ7m�I\��\\ɢ\\ZfN�u4��ou\�ShU\���k�\'<t�-)3}�rN\0V\��RN�\0\�Y\�zQk���\�N��\�\�~\��\0\�G�7h_��5�23\�}�ǭ&\�Jr\�\\1��ɧ+�O\�$\����\�q�>\�l\�tѼ�\�#X\�c�\\�S��\�_%\�\�p\�b&3\�zC\'L\�\�\�\�?\�I�\'�M\���?\�\n^\�\�\�\�ث\���s�\�\�mA�jz\�7Db�\�}�;�\�O�Cy\�qA~>\�i�\\;��~u!�\��_�M/oO������I�\�[\'\���\0���1M�ƷPL���\�K\��~\�FͼW1�\�@\�}k�\��ç\�nX�����?�zH\�,K..A��R�\"�\�e+\�;�A��XI\ZRG�\�^#�N��\�sǡ���[�_�Y�\�\�@\�kQ|7�B��\�\��{�\0��+\�V-�(�\��M�F���\�\��\Z�;<q�\�~AI�\�\�Y�W2�u�i8�W�M\�q\";\�U�ǖ	�\"	\��i�\�l.X�ʖkqwqi:g�]pE-��\�Vr;\�Uq\�\�\�\�\�\�vZ1?\�5P��l�����ukOm\'�\�(յ\�.�\�\0+�����C;K5\�\�p��\��\0��R*���*\n�/�uY\r\�\�\0���-٢Q]��.�\0���׊+��T�-�\�O�\�EE�q\�v7X\"�d�cs\�Gjt� e|�\�-6E�ќ��\�\0\�`ME\�1\�I��4e�\�~V�9\�?���\�gya�\�\�F�I\0\�!F\�9<T]\�+�0m\\\�$�i���T�8�\�U}E�ޑ����I\�=hi\�UfBY�\�Z�\�\�Q�\�r\��Հ\�KP���\� �wPC�)\�zU/�ʊ�\�O�z\�\�\�\\I��\��ҳ\�8\�`�0}I\�K�\�U\n�͞�g_Ʋ`������\�\�n�$72P\�ASպ\n�EsN�^G%\n�3�\�\�A�L�鲍�q�?@i�I\Z��?nvqU\�D-�Y�	\nkq��}-\��\�Io\n�kSe\�,%$��E8\�P���\�7�\�������V(Y��9⓺\�i\�q�9�ycv\�<��\�$���c\�]χ\�\�g�\�]\�$��6Y2��{\�\��G�����\�~\r�\0ץ38?)`\�5�<�1\�L����\0�:2\�%\�z`\�\�r\�\�7.|�\�sO�һ�g�Q\�!�\�\�˒\�R\�r:H\�*�F\�mIn�\�m�8�x��F|�\�א\�\�\�\�0.y�3\�d\�_\�\� \�\�@���J\�Cx��NV�A\�մ���\"�܃�jQ�\�qos�̅�\�\�\��\"\�(�mh�\�+��\�T\�5��y�?\�Y�����Gh\�#v\�\�T�pp9�\0�L~\�6\�`EL.�I�\Z5@O&�\��\�A�x\�%\��V��s�j�\� �\�49�%g\\�\�\���\�\�c1�<��Jҟ\�\"�\�d\'ك\n�����d)nM5$,�s`yG�H\�%!cF���<K\�=���\Z��\�\�H#��\\Ӹ�ɷ.Ah[�i߹enNj���0\���@��H���@}zP+2\�X�`H\�܊��\�P\'٪�O1\�\�\�R	\�`�&�\Z\0��cn��\\f���\��\�jd�8�7��`	Qګ���^)�Ћ[6���\�4\�0C\�W�w\�U>\�2zʫ�J\�Ԭ\�yC��SV\"կ-�c�e#\�Ȭ϶`ߜ\�v4���n��S�}�\�\�ڼ��9�͟\�Z�I�O���=\�ʸ\�z�9���ly\�\�.DO��\�\��)zMj\�/�5f/X\\�\�� 7�\�y\�6\�!\�z�\�|����rvg�.�os�\�\�\�\��\0L\��\�RM{��-\�;�/\��y�O!\r�Ӂ\�S\�y9v\�\�╤�\�w\�\�	�!^mF�\0M,��\'�\�,Dz�d��Y�?�rP��Y�a/$Ǧ����Y�\�̜�\ZZ�4\�\�CZ�e6\�\�Q\�\�\�:̊I��l��S��\��-�#7\�\�Wq�_݂g�g�\0y��夓\r󣕾�\�\�\�F�Kۉc�1Ai;\�h\���&�\rZ�����\'��\�\���>WR�\04G�5a\n���\�ִ\�Y���L}|�Q�M8:�\�?҉|W��\�O�%?\�^o���*ߝ\"�9�/ҕ�\�\�I�\�v&2Ғ�vL�#�\�N��]HI\�@+\�\�q�_ݏ�3t��dgu7�\�1XJ@���\0����>�@V+\\�$�\�\�\�\�7�J<\�c{\Z\�`�<�o�)�\0f ��/|T\�mo�\�)��D��Q2[���IP�\�H\�\�0�֧��Ǜ��\�ʨ?�E/�\�)&����\�\�J\��G�\�?\n�@��\r-CCB\�Y�N�7*��`���\0QZRx\�\�E*d�A\�G��u\�\��\0\\?i�\�y�\Z7�2�\�4��\n�?\�(�?U�iKm\'(x����U	�(�\\\�\����N;�S�C�p\���p�\0>�b�\�����ʻ��\�x\�\�D�J/<nS\�@\�42d,փ�\�Ƹ��pc<}j��\�Ӛ9c\�\\Ϲ\�I\�]6\�\�\�\�ʚ�u\�\�\�{ 3\�<W$d@\�ێ�\�x�`~�rǰsK�\�.�y�?�-\�FO��\�H�nD\0�\��\�q+*(\�r:u2M�s�J-�\���_�$2(;�˖�����\�\���\Z��\�\�ҹs0ʁ(\�\�J&جL��z\�Ӱ]��#��\�\�\�\��\�\�Wmvc�R\��\�\ZɎ\�pz�\�S<\�y\��b��˯_\�\�ȱ�\0��Uy5kɘy�2�m檋�#\'\�#>ԋ.\��\�@h=\�\�~fs�sH�Fz��MV�\��\�\�\r5�%\n�r(\�\�	\�\�U\�d8?�V�D��/��=*<ɀy�;��\�\�=jx�v�Q\���K\��Z�$\�\0q��B\0	���ɤ3�\�v����\�a�f2c���;+�<Aקh;2I�#\0\\�4T�E�f$ۀL�<\�|�\�Z\�1\�+�2\��iѧ�27\��0�\�7,;\n�,Q͌B\�W\�9��K�آF\�\�@\�\�\�C[۰U�6f\�p�4b\�\�q�\"c�s\��)\�\�OGa\�\'zVc�!�<)�\"\�0+[�\�Ī��\�?�]fK1UǵF�\�9fD%�ݩ4D@P\�� \��6�V%\�ӟ�V��&\�9=xj{�#��i=0rj�\�\�\�\"-�S�{\�R��Dm|�霜T���\Z��\�<�V��!e�\'�\�?�+�\�(wc�\�U\�C-��\n\�}�kP.\�ٰ�:g&��Q��q��\nI��a�I�<a˳\�\�8�1\�!!R%�<ջUͤR:(\0\0->U\�``d�0)rݍ;\"4�\";3���Q4\���3�U4Q\�:\�\�T�\��\n*��\Z\�ҎV>b��\�@�v\�)\�\�;�\�\\�*r��m\�#�5nػC\�u\"�(\\�kX\�$���?!$�R�²�\�\"�\�\�~�\�Az�&\��\�pEOo�S�,Y�\�\0ӷp�J_�̉��<1�9\�Q�9\�\�\�k\�\"F�\�)\�\�u\�\�Lm\�E�\��l\�#��r6��\0Z�\�\�Q�2\�\�Z�0rH\�t��6�b}	=?\n,)5�ԩU\0\�dc\�K��\0Ґ$S�����V\�ճ \�#�H����PF3L.T�G2I�\�##���֢:-�ͅ�F \�q\�,։B\n�6\�\��U��\�\��v�é�=itx\�*��n~fl�(m+Op�\��ٶ\rk[\�Y\ZB��`y�UXc��U*\�\�\�\�ژ\\�<3�\�&\��=��w���\�+\\1�\�;tM�Y��rz\�l\�r\�fǩ\��v\r#��\0�z\�U3K8\�\n�7�,\�qݖ9\�p2��k��̲�$q���h\��ԎO�C9��#\�5\\\��\�\�Q��\"\�\�X 0�e�\�OoCI�\nq�\����\�lv�V9\��\�\�Jը\��\�5u]��y\�76O*0�@a�\� �[��\�ƍ)V6�[<\�uMe\n\�\�\\c��I\�P���`�\�T|\�\�#��H9Q\�G�\\:\r��_�ݡ�Y�!mCw\�Wl�\�7�Wp \��\�Y�P��\�9{\�saȎiN0M�Ϧ\rU�\�HۛR1��C�&�A\�T��zT\�nv��bA�\0P�\�\�y�\�(\�n\�?ZCaG\�\�>�5\�R\\ ]�\�f�1E���h�\��[�\�\�\�\�yچ���\�\�W$��S\�c^�\�V̡��l��*\�i\ro��\�M��\���A\�yn\�1ڲ��Zs.pC˜W�[h�6\�(��G��\�Њ�4\�f�c�A=���|���m���\�tzӆ�2�\�\�^{�Z�	4\�Q�d�\��\�2�#��\�\�y�ti:��!\�\�	P�I�ꆜ\�L\0\���*�|\�6E�ա��Ppk\'J��Xo�#�\\\�|�������X�\�\�@��\�\"Ir�3\"^�\�F�\�.\�(9\�%!\�tͤ��@��Y8{O!�?3\�̷}�\�\�S�ː̇�j�D\���\���\0�D����\��V\'\0m�\�ٞV\r\�+gg\�)L\\r��\�M�\���Mi�*��֫M�\�c,\n�=(��=�\�\�n3�_Ҭ�N\�0`7q�b�&\r\�W	\'n@\��P����\�\�b7F<T�SUٜ\�\�O*#3)�}:ר�\0gD��i7�:	�EA.��ݻ�\�S�\�/h7O�\�H\�?�{T%؁�&^85\����0`�b|\��H��],�\rżo��/\���~\�X�f\�\��\�/�\��`�s׊�\�𽣾\�\�\��/֘��L\�h\�\�O��\�ٞp\�\�s���a�W\�=Ez3xNЏ�3�v�R/�\�.2#�C��\�8�(��=�<�.�LFpj\'�S���u\�rxO�Af�q�ޒO\�\�v��lQ\���<�\�>\��\�Ӯh~\�KD\�=�^����\�*!>�wP<+i��=\���\�h�\�\�\�щ\�\�1\�G\�R��c.=�zI���ƅ`�0X��0Т\�\�?��^\�ٞd\�\�.-�q\�B�!�����N�\�Um�]q�1Q�:0W|�/{@�g��~\���&�!\r�\���ק.��\��\�i\�l\�`�h���g�O+e\�\�S\�b\�\�;��C�D�?\0dz�\\];\��\0:Jcpr\n�Q\�\�\�:���\�\�@FS��\�U��\�@��#ۥwI�)b\�\�v\�����M\�\�-�\�&�\�e*h\�|$��\0��\�<dqV\�\�vq]��<�\�]\\�m\�X��\�1P\�ˌ)@}�\�\�lj)\�\�b\��@M6m.(o�\���ךފD�#�B\�\�}f\�3��\�M�\�˦C)�4#\�S͸\\�@?\n�VDA\�4\�0C9\�Ӛ\�̻�\r�w&:QR+DT.\n)Xw+d	�8\�T\����Ж_-�\\\�~\\n�{U��E�1\��c�j�I�-9$~<�WE�k�,1MR��9\�.0Oӭ1mZH\�@\n�s�\n�W8_/�9=*&iVe,5S��\�ﯵ X\�h���\�>���E��\�\"�\�aq��Ќ�\���\�\��/\�Ҿ�\�\�Z,�g����ZF�����*�Q\�7�B�9��b���oi?�[��(4�3���pF\��\0Z|��\�<�ň��\�\�W~\�p�rO��$*�<��\0Th�B�\�S���5R��\�K�*��>�\\V��cF$l$`����\�Uf�<8\�7�\��(���_��7d�\n\�=�*\�\�\�P��;\�/Z9bH\�\"Ί��Ξ�+�U��?�O(\�^A�\��@\�Ƥb\�\�h��.<�\�D\���\�.\�謘\�&I4c[��?\�\�۽*X�F2z��}:\�\�Z�A\���\0\�R��6\�F �\n��|\�+�\�� �\�y*q�Z�<�9�;(���=��]da!*�cm2[he(z�<S���T)�\�� ~\�p��R9D��\�t\�s\�X�\�X��\��\�\�ߠ���X�\�+�H**VC���\�s�qM��dh�ORÚ� �s\�\�\�\�\��\�$3;�\�X\�\�N\��)��F�&0�h\�AP`�)7-��AۿZ�\��Zl\�`~�B8d\�H屌��\0=U\0 Hw$sRIrJ*�Q遚dvѬfX\�\�\�\�J�j\�\���Ҳ�x�F\�b�~l��)�\��y�\�\�.�\nSc(�\079�)d�\"݊��e�\�\��D�B��m\�tϷ�>[m���\�A\�ҡ�V�\'�<\�#\�j���jD\�}\�FC�$�\�I�$�ʁV\\���m\�=�j�4\�\��!@�\��T�8�\\�9��\0�o\n��8$�\��i�)M4K1YT��h\�l>޹�-c�V\�M�d\�������)B���bz�0>�\�WL۠W�I*8?_JHH)y\�ҋ�\�\0H>���C����79-��؊v����#�,�\r��#���\���v���\"�F\�+ƫ.Ѵnm\�U�n$��m\��r�\�cs�>\��S\��\�\�G\�(\��$�M\�\n�s�u��V@b�&\��U\����Kyc\�j;�s\�5,\�l�ɳl#y 䨤�;[\�w.\n�~b2?\Z��GC��F*\0�x\�H\Z/$#YH\�23\�GoƤI���S\�dt>\�\�O��2\�!\'9\�$��y��ș@��rq��g\�R\�p�0\�\0y$�i\�x�V\n�\�p_JA:K�M	X�\��,x\�+\�K\�w.\�ׂ\�A�\0=*4�(\�\���^\0\�wV������\�%\0���EJ��\��\���٢2*��\����\�T\�&�\�\0\�n�n޵��kv\�IU��0xڠ�-#u�:\00��9)o��\�uQ\�>\�Kpp}��F)�\�G�\"�\���I�\�V�8!`ʤ�9\�]G\�\�Pcus\�@�\Z�c\����\��-�A\�\\ya2 R�~b\�NO�Ih��#G\\�44d~z+�dl\�\�9\�V\\<|��\�\0�EB����x4褎F�l?|G֋ǉ.$$yHA˵X&/+��Dr{Ui4g\����\'Ǵ\r\�>�\��Tr�\�Kqk�dS��w��XE}�\�m�\����RY�B6T\0\�j3r\�ǒ�p0Cp��E�lδ�<�|\�~Уw/�=�kJF\�c\�U0!o���}���\��\0�H�w�\�q.>S��\�bL}\�Ė��H\�\�\�Ҫ6��\��J\�\��j\�r��R�;Fq��C\�A�%*����Q\�!�ނI6\�~����i@RrW@�5��ێ#<���\�$ٵ�\��H�����L]ί���#�\�\Z|w�F\�\�Nq\�n\�d\�&Xoۓ�	\�Uym�K��JF	��A5�\�G�d\�\�\�{Rj�E��\�\�3�֕\�\�c2\�Tr*�\�pۜ\�\�g��~tX.Y�T\����c�\��4\�m\\�g�\n\�v\�\�X��\0n�\��Tmn\��C�rh�\\\��\�b�e\�@��Ļ�˟J\�Eq�dJx9\�?\�D\�D����\�{�,;�+\�Vc�\'�J�\�\�\�L���\�Y\�`*dt\�\�8\���s1l�\�r\r�w2\�\���<��l�V&XpN+8<ȼ��\�\�s4Ϳj��E��\n!r�\\\\�ns�c�G��\�<�1��Ţ#\� ��4\�\�K�\�8>\�VB�4\�хs���\�\�\�d\�#W#�,GT\�/�>\�W����Cp̪U&W\\��s�9P��;j\�U��}sL��$p˜�\�\�\��2#��2FN*ܖrڅth�ʍ\�~���w�˴�\"9�=j��%\���W���\0n�\�,\r��j9\��Ū\�\�㝼�*��nem��>��R\��:\�V7\�9eXB\�}\�Y\�=j[i�l�ۣ�}1�zҰ\\�3�D,~�EW���MA�\�)\��!ݛ�C�R�\�\�s�\�O�>\�\�=�\�J(�3p�v�$pjimRs��@\�\�E�\�n�\�\�\�!	,7�N(��\�D\�i�Ԟ�\�W�h���\�8����\�\�nB:\�\�\�=(��\�l�\�[���\�\�J��yPr@\�E@L\0}���\\��\�Q��UFq��QH	��\�\�D�d7 P#,\�$|�QHb �=r\�PD���#����cb����l\�y\�֦E\�1\�Ί(�ݟ�<;z\�.\�9\'\�?Z(�C:\�R�\�,4\�2#��)q����b.L�-�!�c�b�2��:QE\0*0`�g�ZE���\�A c�R\Z\'h�]\�}�Ah̎\�����C!hًa�\�Q��kX�\0\�s�3E��� �O�W9\�=)�F����m�6Oppj�UW�\�0f\'?\�\�?Z(�e=?i\�eER�p��\�\� \����Z�\�3��I�UHЕT�fߘQ\�\�֪��\\�̌O\�\�MP2U��iZ2���+�*�a �(�h^\�Q@�q&f\��)��\�\�L0X���:(�\'�K-j+_��Zi��䑑Zr\��\�ɢ�L�D!�X\�\�{�B��<\�\�\�\�\�4QH�\�!D��c�2�Π�ݤ_\�Ǒ�u�P�!��\�\�Ao1_#�i\�\�@�ޘ\�P�r�q\�\�8\�GS�\�\�ݛS\�\�c\�\�{QE.V\�0d�2X�*;}�\�h\�X\�m�\�=���\0�L\�<\�\�*y\���ӊ(�$�\�v\�\�\��H����\�z(�C�*�\�\��Փm۰[o\�\����.QU���$Pa��P�\0	�a��L\�b�\0��lC~͖�21�\�V�LRƛ�,	\�\���E��TY\�n\�\�py\�0�iL`�\�9�\�E%�\�\��`8f���#�\�W\n�h�� 1\'�S$��^F�Y�w`�\�:\�%1$,\��\r�\��;QE\01�pH\�\"�\�e����!�2�`\�9>�Q@\�H�2$,\�$����`\�@x\0�֊(@\��N\�\�*�\�\�?&��O�=�cx��\�\0}(��X����[z.\�\�晸��4QE��5��\�\�%��\�Wg(C���QE b�1\�ȳ>s\�I��\�)(�s��\�QM	��,�ck�\��\�E#�ufۖ��\�E`#)�\�%M�a�|ߝO2�9�B\�j9\�C:(�:�5]V0\n\"\��(���\��\�','0','5e avenue','Grandes-Piles','G0X 1H0','Quebec','Canada');
/*!40000 ALTER TABLE `site` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `unit`
--

DROP TABLE IF EXISTS `unit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `unit` (
  `Unit_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Unit` varchar(100) NOT NULL,
  PRIMARY KEY (`Unit_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `unit`
--

LOCK TABLES `unit` WRITE;
/*!40000 ALTER TABLE `unit` DISABLE KEYS */;
/*!40000 ALTER TABLE `unit` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `urban_characteristics`
--

DROP TABLE IF EXISTS `urban_characteristics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `urban_characteristics` (
  `Watershed_ID` int(11) NOT NULL,
  `Commercial` float NOT NULL,
  `Green_spaces` float NOT NULL,
  `Industrial` float NOT NULL,
  `Institutional` float NOT NULL,
  `Residential` float NOT NULL,
  `Agricultural` float NOT NULL,
  `Recreational` float NOT NULL,
  PRIMARY KEY (`Watershed_ID`),
  KEY `fk_Urban_Land_Use_Watershed1_idx` (`Watershed_ID`),
  CONSTRAINT `fk_Urban_Land_Use_Watershed1` FOREIGN KEY (`Watershed_ID`) REFERENCES `watershed` (`Watershed_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `urban_characteristics`
--

LOCK TABLES `urban_characteristics` WRITE;
/*!40000 ALTER TABLE `urban_characteristics` DISABLE KEYS */;
/*!40000 ALTER TABLE `urban_characteristics` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `value`
--

DROP TABLE IF EXISTS `value`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `value` (
  `Value_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Date` date NOT NULL,
  `Time` time NOT NULL,
  `Value` double NOT NULL,
  `Number_of_experiment` tinyint(4) NOT NULL,
  `Metadata_ID` int(11) NOT NULL,
  `Comment_ID` int(11) DEFAULT NULL,
  PRIMARY KEY (`Value_ID`),
  KEY `fk_WaterQualityValue_WaterQualityInformation1_idx` (`Metadata_ID`),
  KEY `fk_Water_Quality_Value_Comments1_idx` (`Comment_ID`),
  CONSTRAINT `fk_WaterQualityValue_WaterQualityInformation1` FOREIGN KEY (`Metadata_ID`) REFERENCES `metadata` (`Metadata_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_Water_Quality_Value_Comments1` FOREIGN KEY (`Comment_ID`) REFERENCES `comments` (`Comment_ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `value`
--

LOCK TABLES `value` WRITE;
/*!40000 ALTER TABLE `value` DISABLE KEYS */;
/*!40000 ALTER TABLE `value` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `watershed`
--

DROP TABLE IF EXISTS `watershed`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `watershed` (
  `Watershed_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Watershed_name` varchar(100) NOT NULL,
  `Description` text NOT NULL,
  `Surface_area` float NOT NULL,
  `Concentration_time` int(100) NOT NULL,
  `Impervious_surface` float NOT NULL,
  PRIMARY KEY (`Watershed_ID`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `watershed`
--

LOCK TABLES `watershed` WRITE;
/*!40000 ALTER TABLE `watershed` DISABLE KEYS */;
INSERT INTO `watershed` VALUES (1,'Grande-Piles (sanitary)','Separate sanitary sewer network of Grandes-Piles municipality',0,0,0);
/*!40000 ALTER TABLE `watershed` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `weather_condition`
--

DROP TABLE IF EXISTS `weather_condition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `weather_condition` (
  `Condition_ID` int(11) NOT NULL AUTO_INCREMENT,
  `Weather_condition` varchar(100) NOT NULL,
  `Description` text NOT NULL,
  PRIMARY KEY (`Condition_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `weather_condition`
--

LOCK TABLES `weather_condition` WRITE;
/*!40000 ALTER TABLE `weather_condition` DISABLE KEYS */;
/*!40000 ALTER TABLE `weather_condition` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'dateaubase'
--

--
-- Dumping routines for database 'dateaubase'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-03-23 17:11:51
