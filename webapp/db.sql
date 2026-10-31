-- MySQL dump 10.13  Distrib 8.0.25, for macos11 (x86_64)
--
-- Host: localhost    Database: authbase
-- ------------------------------------------------------
-- Server version	8.0.25

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `SYONLINE`
--

DROP TABLE IF EXISTS `SYONLINE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYONLINE` (
  `ID` bigint NOT NULL AUTO_INCREMENT,
  `CREATEDATETIME` datetime DEFAULT NULL,
  `IP` varchar(100) DEFAULT NULL,
  `LOGINNAME` varchar(100) DEFAULT NULL,
  `TYPE` varchar(1) DEFAULT NULL,
  `BROWSER` varchar(50) DEFAULT NULL,
  `OS` varchar(50) DEFAULT NULL,
  `LOCATION` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`ID`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYONLINE`
--

LOCK TABLES `SYONLINE` WRITE;
/*!40000 ALTER TABLE `SYONLINE` DISABLE KEYS */;
INSERT INTO `SYONLINE` VALUES (1,'2025-08-19 20:35:16','127.0.0.1','admin','0','Safari','Mac OS','鍐呯綉IP'),(2,'2025-08-19 20:35:23','127.0.0.1','admin','1','Safari','Mac OS','鍐呯綉IP');
/*!40000 ALTER TABLE `SYONLINE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYOPERATIONLOG`
--

DROP TABLE IF EXISTS `SYOPERATIONLOG`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYOPERATIONLOG` (
  `ID` bigint NOT NULL AUTO_INCREMENT,
  `OPERATION_NAME` varchar(100) NOT NULL,
  `METHOD` varchar(10) DEFAULT NULL,
  `PATH` varchar(200) NOT NULL,
  `PARAMS` text,
  `CREATEDATETIME` datetime DEFAULT NULL,
  `OPERATOR` varchar(100) DEFAULT NULL,
  `OPERATIONTIME` int DEFAULT NULL,
  `RESPONSE` text,
  `EXECEPTION` text,
  `RESULT` int DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYOPERATIONLOG`
--

LOCK TABLES `SYOPERATIONLOG` WRITE;
/*!40000 ALTER TABLE `SYOPERATIONLOG` DISABLE KEYS */;
INSERT INTO `SYOPERATIONLOG` VALUES (24,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 10:03:57','admin',0,'<Response 46 bytes [200 OK]>',NULL,1),(25,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 10:12:29','admin',0,'{\'code\': 200, \'msg\': \'淇敼鎴愬姛\'}',NULL,1),(26,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 10:14:44','admin',0,'{\'code\': 200, \'msg\': \'淇敼鎴愬姛\'}',NULL,1),(27,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 10:22:55','admin',1301,'{\'code\': 200, \'msg\': \'淇敼鎴愬姛\'}',NULL,1),(28,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 10:26:18','admin',1303,NULL,'娴嬭瘯寮傚父',0),(29,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 21:56:09','admin',194,'{\'code\': 200, \'msg\': \'淇敼鎴愬姛\'}',NULL,1),(30,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 21:56:20','admin',193,'{\'code\': 200, \'msg\': \'淇敼鎴愬姛\'}',NULL,1),(31,'淇敼瀵嗙爜','PUT','/system/user/profile/updatePwd','{}','2025-04-09 21:56:44','admin',191,'{\'code\': 200, \'msg\': \'淇敼鎴愬姛\'}',NULL,1);
/*!40000 ALTER TABLE `SYOPERATIONLOG` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYORGANIZATION`
--

DROP TABLE IF EXISTS `SYORGANIZATION`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYORGANIZATION` (
  `ID` varchar(36) NOT NULL,
  `ADDRESS` varchar(200) DEFAULT NULL,
  `CODE` varchar(200) DEFAULT NULL,
  `CREATEDATETIME` datetime DEFAULT NULL,
  `ICONCLS` varchar(100) DEFAULT NULL,
  `NAME` varchar(200) DEFAULT NULL,
  `SEQ` int DEFAULT NULL,
  `UPDATEDATETIME` datetime DEFAULT NULL,
  `SYORGANIZATION_ID` varchar(36) DEFAULT NULL,
  `LEADER` varchar(20) DEFAULT NULL COMMENT '璐熻矗浜?,
  `PHONE` varchar(11) DEFAULT NULL COMMENT '鑱旂郴鐢佃瘽',
  `EMAIL` varchar(50) DEFAULT NULL COMMENT '閭',
  `STATUS` varchar(10) DEFAULT '0',
  PRIMARY KEY (`ID`) USING BTREE,
  KEY `FK_acf7qlb04quthktalwx8c7q69` (`SYORGANIZATION_ID`) USING BTREE,
  CONSTRAINT `FK_acf7qlb04quthktalwx8c7q69` FOREIGN KEY (`SYORGANIZATION_ID`) REFERENCES `SYORGANIZATION` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYORGANIZATION`
--

LOCK TABLES `SYORGANIZATION` WRITE;
/*!40000 ALTER TABLE `SYORGANIZATION` DISABLE KEYS */;
INSERT INTO `SYORGANIZATION` VALUES ('0',NULL,NULL,'2016-11-28 10:34:54','ext-icon-bricks','鎬婚儴',100,'2016-11-28 10:35:12',NULL,NULL,NULL,NULL,'0'),('5477d9a9-e41e-485f-bb08-697e8facef88',NULL,NULL,'2022-05-22 09:59:33',NULL,'鍗椾含鍒嗗叕鍙?,1,'2023-05-16 19:52:10','0','dd','18905189016','ss@ada.com','0');
/*!40000 ALTER TABLE `SYORGANIZATION` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYORGANIZATION_SYRESOURCE`
--

DROP TABLE IF EXISTS `SYORGANIZATION_SYRESOURCE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYORGANIZATION_SYRESOURCE` (
  `SYRESOURCE_ID` varchar(36) NOT NULL,
  `SYORGANIZATION_ID` varchar(36) NOT NULL,
  PRIMARY KEY (`SYORGANIZATION_ID`,`SYRESOURCE_ID`) USING BTREE,
  KEY `FK_acpjp8a7fjo0cnn02eb0ia6uf` (`SYORGANIZATION_ID`) USING BTREE,
  KEY `FK_m4mfglk7odi78d8pk9pif44vc` (`SYRESOURCE_ID`) USING BTREE,
  CONSTRAINT `FK_acpjp8a7fjo0cnn02eb0ia6uf` FOREIGN KEY (`SYORGANIZATION_ID`) REFERENCES `SYORGANIZATION` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FK_m4mfglk7odi78d8pk9pif44vc` FOREIGN KEY (`SYRESOURCE_ID`) REFERENCES `SYRESOURCE` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYORGANIZATION_SYRESOURCE`
--

LOCK TABLES `SYORGANIZATION_SYRESOURCE` WRITE;
/*!40000 ALTER TABLE `SYORGANIZATION_SYRESOURCE` DISABLE KEYS */;
/*!40000 ALTER TABLE `SYORGANIZATION_SYRESOURCE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYRESOURCE`
--

DROP TABLE IF EXISTS `SYRESOURCE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYRESOURCE` (
  `ID` varchar(36) NOT NULL,
  `CREATEDATETIME` datetime DEFAULT NULL,
  `DESCRIPTION` varchar(200) DEFAULT NULL,
  `ICONCLS` varchar(100) DEFAULT NULL,
  `NAME` varchar(100) NOT NULL,
  `SEQ` int DEFAULT NULL,
  `TARGET` varchar(100) DEFAULT NULL,
  `UPDATEDATETIME` datetime DEFAULT NULL,
  `PATH` varchar(200) DEFAULT NULL,
  `URL` varchar(200) DEFAULT NULL,
  `PERMS` varchar(100) DEFAULT NULL COMMENT '鏉冮檺鏍囪瘑',
  `SYRESOURCE_ID` varchar(36) DEFAULT NULL,
  `SYRESOURCETYPE_ID` varchar(36) DEFAULT NULL,
  `STATUS` varchar(10) DEFAULT '0',
  `VISIBLE` varchar(10) DEFAULT '0',
  PRIMARY KEY (`ID`) USING BTREE,
  KEY `FK_n8kk2inhw4y4gax3nra2etfup` (`SYRESOURCE_ID`) USING BTREE,
  KEY `FK_93qfpiiuk3rwb32gc5mcmmlgh` (`SYRESOURCETYPE_ID`) USING BTREE,
  CONSTRAINT `FK_93qfpiiuk3rwb32gc5mcmmlgh` FOREIGN KEY (`SYRESOURCETYPE_ID`) REFERENCES `SYRESOURCETYPE` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FK_n8kk2inhw4y4gax3nra2etfup` FOREIGN KEY (`SYRESOURCE_ID`) REFERENCES `SYRESOURCE` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYRESOURCE`
--

LOCK TABLES `SYRESOURCE` WRITE;
/*!40000 ALTER TABLE `SYRESOURCE` DISABLE KEYS */;
INSERT INTO `SYRESOURCE` VALUES ('27fda67f-61d1-4fe6-8eea-d796a848ab67','2022-05-28 12:54:39',NULL,'edit','鍙傛暟璁剧疆',6,'','2022-05-28 12:54:39','config','system/config/index','system:config:list','xtgl','3','0','0'),('37ac3cd3-560b-49b3-ae86-96d1963e9db6','2022-05-28 12:55:59',NULL,NULL,'鍙傛暟淇敼',3,NULL,'2022-05-28 12:55:59',NULL,NULL,'system:config:edit','27fda67f-61d1-4fe6-8eea-d796a848ab67','1','0','0'),('4621e9f8-e7c6-4c2b-8172-3d8c8ea75371','2022-05-28 12:55:24',NULL,NULL,'鍙傛暟鏂板',2,NULL,'2022-05-28 12:55:24',NULL,NULL,'system:config:add','27fda67f-61d1-4fe6-8eea-d796a848ab67','1','0','0'),('5dda42e6-a844-43e0-b211-757291201ad0','2025-04-10 21:19:52',NULL,NULL,'鏈嶅姟鐩戞帶',1,NULL,'2025-04-10 21:19:52',NULL,NULL,'monitor:server:list','eab33e77-28b4-4f05-9c42-99b88d605264','1','0','0'),('71d62d9c-a70a-48a6-9319-8cd161ee72db','2025-04-08 21:10:20',NULL,NULL,'娓呯┖鎿嶄綔',5,NULL,'2025-04-08 21:10:20',NULL,NULL,'monitor:operlog:clean','e6d71448-a612-46c2-a9e1-2dfcd3ea745c','1','0','0'),('726c7c1e-06f8-4c3e-b9e1-95778a430c07','2022-05-28 12:51:16',NULL,NULL,'瀛楀吀鏌ヨ',1,NULL,'2022-05-28 12:51:16',NULL,NULL,'system:dict:query','ffb8cf26-1049-43ee-9dd5-16e5742ce9d5','1','0','0'),('830bb1dd-2bb1-4364-bf46-d12421627d45','2025-04-08 21:07:00',NULL,NULL,'鏌ョ湅鎿嶄綔',2,NULL,'2025-04-08 21:09:13',NULL,NULL,'monitor:operlog:query','e6d71448-a612-46c2-a9e1-2dfcd3ea745c','1','0','0'),('8960e08b-1258-4bf0-94c9-5cd47702f00e','2025-04-08 21:06:08',NULL,NULL,'鎿嶄綔鍘嗗彶',1,NULL,'2025-04-08 21:06:22','',NULL,'monitor:operlog:list','e6d71448-a612-46c2-a9e1-2dfcd3ea745c','1','0','0'),('b95cae69-6389-4ebc-b613-bee7aac5f730','2022-05-28 12:52:26',NULL,NULL,'瀛楀吀淇敼',3,NULL,'2022-05-28 12:52:26',NULL,NULL,'system:dict:edit','ffb8cf26-1049-43ee-9dd5-16e5742ce9d5','1','0','0'),('cc7ff599-a588-40b3-951d-ce9dd2490482','2022-05-28 12:53:26',NULL,NULL,'瀛楀吀瀵煎嚭',5,NULL,'2022-05-28 12:53:26',NULL,NULL,'system:dict:export','ffb8cf26-1049-43ee-9dd5-16e5742ce9d5','1','0','0'),('cssc','2022-05-28 12:56:23',NULL,NULL,'鍙傛暟鍒犻櫎',4,NULL,'2022-05-28 12:56:23',NULL,NULL,'system:config:remove','27fda67f-61d1-4fe6-8eea-d796a848ab67','1','0','0'),('d60df8ae-86ee-4879-b9b9-2fe79f146d31','2022-05-28 12:55:02',NULL,NULL,'鍙傛暟鏌ヨ',1,NULL,'2022-05-28 12:55:02',NULL,NULL,'system:config:query','27fda67f-61d1-4fe6-8eea-d796a848ab67','1','0','0'),('dd41b52b-272c-49ac-b045-b05392890a8d','2022-05-28 12:56:49',NULL,NULL,'鍙傛暟瀵煎嚭',5,NULL,'2022-05-28 12:56:49',NULL,NULL,'system:config:export','27fda67f-61d1-4fe6-8eea-d796a848ab67','1','0','0'),('e6d71448-a612-46c2-a9e1-2dfcd3ea745c','2025-04-08 21:03:46',NULL,'log','鎿嶄綔鏃ュ織',2,NULL,'2025-04-08 21:05:02','operlog','monitor/operlog/index','monitor:operlog:list','xtjk','0','0','0'),('eab33e77-28b4-4f05-9c42-99b88d605264','2025-04-10 21:18:14',NULL,'server','鏈嶅姟鐩戞帶',3,NULL,'2025-04-10 21:19:06','server','monitor/server/index','monitor:server:list','xtjk','0','0','0'),('edc3358e-b9c5-462f-8a70-7b1c7d7f2c26','2022-05-28 12:51:53',NULL,NULL,'瀛楀吀鏂板',2,NULL,'2022-05-28 12:51:53',NULL,NULL,'system:dict:add','ffb8cf26-1049-43ee-9dd5-16e5742ce9d5','1','0','0'),('eead451f-969e-4374-a1c3-8acd03a7751d','2025-04-08 21:09:43',NULL,NULL,'瀵煎嚭鎿嶄綔',4,NULL,'2025-04-08 21:09:43',NULL,NULL,'monitor:operlog:export','e6d71448-a612-46c2-a9e1-2dfcd3ea745c','1','0','0'),('eeae423a-62de-4890-9b3c-8aaa19180361','2025-04-08 21:08:58',NULL,NULL,'鍒犻櫎鎿嶄綔',3,NULL,'2025-04-08 21:08:58',NULL,NULL,'monitor:operlog:remove','e6d71448-a612-46c2-a9e1-2dfcd3ea745c','1','0','0'),('ffb8cf26-1049-43ee-9dd5-16e5742ce9d5','2022-05-28 12:50:37',NULL,'dict','瀛楀吀绠＄悊',5,'','2022-05-28 12:50:37','dict','system/dict/index','system:dict:list','xtgl','3','0','0'),('jgbj','2015-08-25 10:34:53','缂栬緫鏈烘瀯','ext-icon-bullet_wrench','缂栬緫鏈烘瀯',2,'','2022-05-25 00:39:56',NULL,'/base/syorganization!update','system:dept:edit','jggl','1','0','0'),('jgck','2015-08-25 10:34:53','鏌ョ湅鏈烘瀯','ext-icon-bullet_wrench','鏌ョ湅鏈烘瀯',4,'','2015-08-25 10:34:53',NULL,'/base/syorganization!getById','system:dept:query','jggl','1','0','0'),('jggl','2015-08-25 10:34:53','绠＄悊绯荤粺涓敤鎴风殑鏈烘瀯','tree','鏈烘瀯绠＄悊',4,'','2022-05-25 00:40:04','dept','system/dept/index','system:dept:list','xtgl','0','0','0'),('jglb','2015-08-25 10:34:53','鏌ヨ鏈烘瀯鍒楄〃','ext-icon-bullet_wrench','鏈烘瀯鍒楄〃',0,'','2016-11-28 14:09:52',NULL,'/base/syorganization!treeGrid','system:dept:list','jggl','1','0','0'),('jgsc','2015-08-25 10:34:53','鍒犻櫎鏈烘瀯','ext-icon-bullet_wrench','鍒犻櫎鏈烘瀯',3,'','2015-08-25 10:34:53',NULL,'/base/syorganization!delete','system:dept:remove','jggl','1','0','0'),('jgsq','2015-08-25 10:34:53','鏈烘瀯鎺堟潈','ext-icon-bullet_wrench','鏈烘瀯鎺堟潈',5,'','2015-08-25 10:34:53',NULL,'/base/syorganization!grant',NULL,'jggl','1','0','0'),('jgtj','2015-08-25 10:34:53','娣诲姞鏈烘瀯','ext-icon-bullet_wrench','娣诲姞鏈烘瀯',1,'','2015-08-25 10:34:53',NULL,'/base/syorganization!save','system:dept:add','jggl','1','0','0'),('jsbj','2015-08-25 10:34:53','缂栬緫瑙掕壊','ext-icon-bullet_wrench','缂栬緫瑙掕壊',2,'','2015-08-25 10:34:53',NULL,'/base/syrole!update','system:role:edit','jsgl','1','0','0'),('jsck','2015-08-25 10:34:53','鏌ョ湅瑙掕壊','ext-icon-bullet_wrench','鏌ョ湅瑙掕壊',4,'','2015-08-25 10:34:53',NULL,'/base/syrole!getById','system:role:query','jsgl','1','0','0'),('jsgl','2015-08-25 10:34:53','绠＄悊绯荤粺涓敤鎴风殑瑙掕壊','peoples','瑙掕壊绠＄悊',2,'','2015-08-25 10:34:53','role','system/role/index','system:role:list','xtgl','0','0','0'),('jslb','2015-08-25 10:34:53','鏌ヨ瑙掕壊鍒楄〃','ext-icon-bullet_wrench','瑙掕壊鍒楄〃',0,'','2015-08-25 10:34:53',NULL,'/base/syrole!grid','system:role:list','jsgl','1','0','0'),('jssc','2015-08-25 10:34:53','鍒犻櫎瑙掕壊','ext-icon-bullet_wrench','鍒犻櫎瑙掕壊',3,'','2015-08-25 10:34:53',NULL,'/base/syrole!delete','system:role:remove','jsgl','1','0','0'),('jssq','2015-08-25 10:34:53','瑙掕壊鎺堟潈','ext-icon-bullet_wrench','瑙掕壊鎺堟潈',5,'','2015-08-25 10:34:53',NULL,'/base/syrole!grant',NULL,'jsgl','1','0','0'),('jstj','2015-08-25 10:34:53','娣诲姞瑙掕壊','ext-icon-bullet_wrench','娣诲姞瑙掕壊',1,'','2015-08-25 10:34:53',NULL,'/base/syrole!save','system:role:add','jsgl','1','0','0'),('online','2015-08-25 10:34:53','鐩戞帶鐢ㄦ埛鐧诲綍銆佹敞閿€','online','鐧诲綍鍘嗗彶',1,'','2026-01-09 20:39:51','logininfor','monitor/logininfor/index','monitor:logininfor:list','xtjk','0','0','0'),('onlineGrid','2015-08-25 10:34:53','鐢ㄦ埛鐧诲綍銆佹敞閿€鍘嗗彶璁板綍鍒楄〃','ext-icon-bullet_wrench','鐢ㄦ埛鐧诲綍鍘嗗彶鍒楄〃',1,'','2022-05-28 13:16:37',NULL,'/base/syonline!grid','monitor:logininfor:list','online','1','0','0'),('xtgl','2015-08-25 10:34:53','绠＄悊绯荤粺鐨勮祫婧愩€佽鑹层€佹満鏋勩€佺敤鎴风瓑淇℃伅','system','绯荤粺绠＄悊',1,'','2023-05-16 20:03:02','/system',NULL,NULL,NULL,'3','0','0'),('xtjk','2015-08-25 10:34:53','鐩戞帶绯荤粺杩愯鎯呭喌绛変俊鎭?,'monitor','绯荤粺鐩戞帶',2,'','2022-06-10 00:48:47','/system/log','','',NULL,'0','0','0'),('yhbj','2015-08-25 10:34:53','缂栬緫鐢ㄦ埛','ext-icon-bullet_wrench','缂栬緫鐢ㄦ埛',2,'','2015-08-25 10:34:53',NULL,'/base/syuser!update','system:user:edit','yhgl','1','0','0'),('yhck','2015-08-25 10:34:53','鏌ョ湅鐢ㄦ埛','ext-icon-bullet_wrench','鏌ョ湅鐢ㄦ埛',4,'','2015-08-25 10:34:53',NULL,'/base/syuser!getById','system:user:query','yhgl','1','0','0'),('yhgl','2015-08-25 10:34:53','绠＄悊绯荤粺涓敤鎴风殑鐢ㄦ埛','user','鐢ㄦ埛绠＄悊',1,'','2023-05-16 20:08:40','user','system/user/index','system:user:list','xtgl','0','0','0'),('yhjg','2015-08-25 10:34:53','缂栬緫鐢ㄦ埛鏈烘瀯','ext-icon-bullet_wrench','鐢ㄦ埛鏈烘瀯',6,'','2015-08-25 10:34:53',NULL,'/base/syuser!grantOrganization','system:dept:edit','yhgl','1','0','0'),('yhjs','2015-08-25 10:34:53','缂栬緫鐢ㄦ埛瑙掕壊','ext-icon-bullet_wrench','鐢ㄦ埛瑙掕壊',5,'','2015-08-25 10:34:53',NULL,'/base/syuser!grantRole','system:role:edit','yhgl','1','0','0'),('yhlb','2015-08-25 10:34:53','鏌ヨ鐢ㄦ埛鍒楄〃','ext-icon-bullet_wrench','鐢ㄦ埛鍒楄〃',0,'','2015-08-25 10:34:53',NULL,'/base/syuser!grid','system:user:list','yhgl','1','0','0'),('yhsc','2015-08-25 10:34:53','鍒犻櫎鐢ㄦ埛','ext-icon-bullet_wrench','鍒犻櫎鐢ㄦ埛',3,'','2015-08-25 10:34:53',NULL,'/base/syuser!delete','system:user:remove','yhgl','1','0','0'),('yhtj','2015-08-25 10:34:53','娣诲姞鐢ㄦ埛','ext-icon-bullet_wrench','娣诲姞鐢ㄦ埛',1,'','2015-08-25 10:34:53',NULL,'/base/syuser!save','system:user:add','yhgl','1','0','0'),('zdsc','2022-05-28 12:52:58',NULL,NULL,'瀛楀吀鍒犻櫎',4,NULL,'2022-05-28 12:52:58',NULL,NULL,'system:dict:remove','ffb8cf26-1049-43ee-9dd5-16e5742ce9d5','1','0','0'),('zybj','2015-08-25 10:34:53','缂栬緫璧勬簮','ext-icon-bullet_wrench','缂栬緫璧勬簮',2,'','2015-08-25 10:34:53',NULL,'/base/syresource!update','system:menu:edit','zygl','1','0','0'),('zyck','2015-08-25 10:34:53','鏌ョ湅璧勬簮','ext-icon-bullet_wrench','鏌ョ湅璧勬簮',4,'','2015-08-25 10:34:53',NULL,'/base/syresource!getById','system:menu:query','zygl','1','0','0'),('zygl','2015-08-25 10:34:53','绠＄悊绯荤粺鐨勮祫婧?,'tree-table','璧勬簮绠＄悊',3,'','2022-05-25 00:48:32','menu','system/menu/index','system:menu:list','xtgl','0','0','0'),('zylb','2015-08-25 10:34:53','鏌ヨ璧勬簮','ext-icon-bullet_wrench','璧勬簮鍒楄〃',0,'','2015-08-25 10:34:53',NULL,'/base/syresource!treeGrid','system:menu:query','zygl','1','0','0'),('zysc','2015-08-25 10:34:53','鍒犻櫎璧勬簮','ext-icon-bullet_wrench','鍒犻櫎璧勬簮',3,'','2015-08-25 10:34:53',NULL,'/base/syresource!delete','system:menu:remove','zygl','1','0','0'),('zytj','2015-08-25 10:34:53','娣诲姞璧勬簮','ext-icon-bullet_wrench','娣诲姞璧勬簮',1,'','2015-08-25 10:34:53',NULL,'/base/syresource!save','system:menu:add','zygl','1','0','0');
/*!40000 ALTER TABLE `SYRESOURCE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYRESOURCETYPE`
--

DROP TABLE IF EXISTS `SYRESOURCETYPE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYRESOURCETYPE` (
  `ID` varchar(36) NOT NULL,
  `CREATEDATETIME` datetime DEFAULT NULL,
  `DESCRIPTION` varchar(200) DEFAULT NULL,
  `NAME` varchar(100) NOT NULL,
  `UPDATEDATETIME` datetime DEFAULT NULL,
  PRIMARY KEY (`ID`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYRESOURCETYPE`
--

LOCK TABLES `SYRESOURCETYPE` WRITE;
/*!40000 ALTER TABLE `SYRESOURCETYPE` DISABLE KEYS */;
INSERT INTO `SYRESOURCETYPE` VALUES ('0','2015-08-25 10:34:53','鑿滃崟绫诲瀷浼氭樉绀哄湪绯荤粺棣栭〉宸︿晶鑿滃崟涓?,'鑿滃崟','2015-08-25 10:34:53'),('1','2015-08-25 10:34:53','鍔熻兘绫诲瀷涓嶄細鏄剧ず鍦ㄧ郴缁熼椤靛乏渚ц彍鍗曚腑','鍔熻兘','2015-08-25 10:34:53'),('3','2022-05-15 10:27:08',NULL,'鐩綍','2022-05-15 10:27:18');
/*!40000 ALTER TABLE `SYRESOURCETYPE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYROLE`
--

DROP TABLE IF EXISTS `SYROLE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYROLE` (
  `ID` varchar(36) NOT NULL,
  `CREATEDATETIME` datetime DEFAULT NULL,
  `DESCRIPTION` varchar(200) DEFAULT NULL,
  `ICONCLS` varchar(100) DEFAULT NULL,
  `NAME` varchar(100) NOT NULL,
  `SEQ` int DEFAULT NULL,
  `UPDATEDATETIME` datetime DEFAULT NULL,
  `ROLEKEY` varchar(100) NOT NULL COMMENT '瑙掕壊鏉冮檺瀛楃涓?,
  `DATASCOPE` char(1) DEFAULT '1' COMMENT '鏁版嵁鑼冨洿锛?锛氬叏閮ㄦ暟鎹潈闄?2锛氳嚜瀹氭暟鎹潈闄?3锛氭湰閮ㄩ棬鏁版嵁鏉冮檺 4锛氭湰閮ㄩ棬鍙婁互涓嬫暟鎹潈闄愶級',
  `STATUS` varchar(10) DEFAULT '0',
  PRIMARY KEY (`ID`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYROLE`
--

LOCK TABLES `SYROLE` WRITE;
/*!40000 ALTER TABLE `SYROLE` DISABLE KEYS */;
INSERT INTO `SYROLE` VALUES ('0','2015-08-25 10:34:53','鎷ユ湁绯荤粺鎵€鏈夋潈闄?,NULL,'瓒呯',0,'2025-04-10 21:20:12','superadmin','1','0'),('19f00d46-8f1b-45b5-b7b7-6197d7b8cb33','2016-11-28 14:24:00',NULL,NULL,'绠＄悊鍛?,100,'2022-06-10 00:27:41','admin','1','0'),('f4e1b151-a171-4705-9154-503a046cb72a','2022-05-29 13:29:38',NULL,NULL,'鍙鐢ㄦ埛',1,'2022-06-10 00:13:55','readonly','2','0');
/*!40000 ALTER TABLE `SYROLE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYROLE_SYORGANIZATION`
--

DROP TABLE IF EXISTS `SYROLE_SYORGANIZATION`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYROLE_SYORGANIZATION` (
  `SYROLE_ID` varchar(36) NOT NULL,
  `SYORGANIZATION_ID` varchar(36) NOT NULL,
  PRIMARY KEY (`SYORGANIZATION_ID`,`SYROLE_ID`) USING BTREE,
  KEY `FK_kkrartsovl2frhfvriqdi7jwl` (`SYORGANIZATION_ID`) USING BTREE,
  KEY `FK_r139h669pg4ts6mbvn3ip5472` (`SYROLE_ID`) USING BTREE,
  CONSTRAINT `SYROLE_SYORGANIZATION_ibfk_1` FOREIGN KEY (`SYORGANIZATION_ID`) REFERENCES `SYORGANIZATION` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `SYROLE_SYORGANIZATION_ibfk_2` FOREIGN KEY (`SYROLE_ID`) REFERENCES `SYROLE` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYROLE_SYORGANIZATION`
--

LOCK TABLES `SYROLE_SYORGANIZATION` WRITE;
/*!40000 ALTER TABLE `SYROLE_SYORGANIZATION` DISABLE KEYS */;
INSERT INTO `SYROLE_SYORGANIZATION` VALUES ('f4e1b151-a171-4705-9154-503a046cb72a','5477d9a9-e41e-485f-bb08-697e8facef88');
/*!40000 ALTER TABLE `SYROLE_SYORGANIZATION` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYROLE_SYRESOURCE`
--

DROP TABLE IF EXISTS `SYROLE_SYRESOURCE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYROLE_SYRESOURCE` (
  `SYROLE_ID` varchar(36) NOT NULL,
  `SYRESOURCE_ID` varchar(36) NOT NULL,
  PRIMARY KEY (`SYRESOURCE_ID`,`SYROLE_ID`) USING BTREE,
  KEY `FK_kkrartsovl2frhfvriqdi7jwl` (`SYRESOURCE_ID`) USING BTREE,
  KEY `FK_r139h669pg4ts6mbvn3ip5472` (`SYROLE_ID`) USING BTREE,
  CONSTRAINT `FK_kkrartsovl2frhfvriqdi7jwl` FOREIGN KEY (`SYRESOURCE_ID`) REFERENCES `SYRESOURCE` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FK_r139h669pg4ts6mbvn3ip5472` FOREIGN KEY (`SYROLE_ID`) REFERENCES `SYROLE` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYROLE_SYRESOURCE`
--

LOCK TABLES `SYROLE_SYRESOURCE` WRITE;
/*!40000 ALTER TABLE `SYROLE_SYRESOURCE` DISABLE KEYS */;
INSERT INTO `SYROLE_SYRESOURCE` VALUES ('0','27fda67f-61d1-4fe6-8eea-d796a848ab67'),('f4e1b151-a171-4705-9154-503a046cb72a','27fda67f-61d1-4fe6-8eea-d796a848ab67'),('0','37ac3cd3-560b-49b3-ae86-96d1963e9db6'),('0','4621e9f8-e7c6-4c2b-8172-3d8c8ea75371'),('0','5dda42e6-a844-43e0-b211-757291201ad0'),('0','71d62d9c-a70a-48a6-9319-8cd161ee72db'),('0','726c7c1e-06f8-4c3e-b9e1-95778a430c07'),('f4e1b151-a171-4705-9154-503a046cb72a','726c7c1e-06f8-4c3e-b9e1-95778a430c07'),('0','830bb1dd-2bb1-4364-bf46-d12421627d45'),('0','8960e08b-1258-4bf0-94c9-5cd47702f00e'),('0','b95cae69-6389-4ebc-b613-bee7aac5f730'),('0','cc7ff599-a588-40b3-951d-ce9dd2490482'),('0','cssc'),('0','d60df8ae-86ee-4879-b9b9-2fe79f146d31'),('f4e1b151-a171-4705-9154-503a046cb72a','d60df8ae-86ee-4879-b9b9-2fe79f146d31'),('0','dd41b52b-272c-49ac-b045-b05392890a8d'),('0','e6d71448-a612-46c2-a9e1-2dfcd3ea745c'),('0','eab33e77-28b4-4f05-9c42-99b88d605264'),('0','edc3358e-b9c5-462f-8a70-7b1c7d7f2c26'),('0','eead451f-969e-4374-a1c3-8acd03a7751d'),('0','eeae423a-62de-4890-9b3c-8aaa19180361'),('0','ffb8cf26-1049-43ee-9dd5-16e5742ce9d5'),('f4e1b151-a171-4705-9154-503a046cb72a','ffb8cf26-1049-43ee-9dd5-16e5742ce9d5'),('0','jgbj'),('0','jgck'),('0','jggl'),('f4e1b151-a171-4705-9154-503a046cb72a','jggl'),('0','jglb'),('f4e1b151-a171-4705-9154-503a046cb72a','jglb'),('0','jgsc'),('0','jgsq'),('0','jgtj'),('0','jsbj'),('0','jsck'),('0','jsgl'),('f4e1b151-a171-4705-9154-503a046cb72a','jsgl'),('0','jslb'),('f4e1b151-a171-4705-9154-503a046cb72a','jslb'),('0','jssc'),('0','jssq'),('0','jstj'),('0','online'),('0','onlineGrid'),('0','xtgl'),('f4e1b151-a171-4705-9154-503a046cb72a','xtgl'),('0','xtjk'),('0','yhbj'),('0','yhck'),('0','yhgl'),('f4e1b151-a171-4705-9154-503a046cb72a','yhgl'),('0','yhjg'),('0','yhjs'),('0','yhlb'),('f4e1b151-a171-4705-9154-503a046cb72a','yhlb'),('0','yhsc'),('0','yhtj'),('0','zdsc'),('0','zybj'),('0','zyck'),('0','zygl'),('f4e1b151-a171-4705-9154-503a046cb72a','zygl'),('0','zylb'),('f4e1b151-a171-4705-9154-503a046cb72a','zylb'),('0','zysc'),('0','zytj');
/*!40000 ALTER TABLE `SYROLE_SYRESOURCE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYS_CONFIG`
--

DROP TABLE IF EXISTS `SYS_CONFIG`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYS_CONFIG` (
  `config_id` int NOT NULL AUTO_INCREMENT COMMENT '鍙傛暟涓婚敭',
  `config_name` varchar(100) DEFAULT '' COMMENT '鍙傛暟鍚嶇О',
  `config_key` varchar(100) DEFAULT '' COMMENT '鍙傛暟閿悕',
  `config_value` varchar(500) DEFAULT '' COMMENT '鍙傛暟閿€?,
  `config_type` char(1) DEFAULT 'N' COMMENT '绯荤粺鍐呯疆锛圷鏄?N鍚︼級',
  `create_by` varchar(64) DEFAULT '' COMMENT '鍒涘缓鑰?,
  `create_time` datetime DEFAULT NULL COMMENT '鍒涘缓鏃堕棿',
  `update_by` varchar(64) DEFAULT '' COMMENT '鏇存柊鑰?,
  `update_time` datetime DEFAULT NULL COMMENT '鏇存柊鏃堕棿',
  `remark` varchar(500) DEFAULT NULL COMMENT '澶囨敞',
  PRIMARY KEY (`config_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYS_CONFIG`
--

LOCK TABLES `SYS_CONFIG` WRITE;
/*!40000 ALTER TABLE `SYS_CONFIG` DISABLE KEYS */;
INSERT INTO `SYS_CONFIG` VALUES (1,'涓绘鏋堕〉-榛樿鐨偆鏍峰紡鍚嶇О','sys.index.skinName','skin-blue','Y','admin','2022-05-14 14:04:21','',NULL,'钃濊壊 skin-blue銆佺豢鑹?skin-green銆佺传鑹?skin-purple銆佺孩鑹?skin-red銆侀粍鑹?skin-yellow'),(2,'鐢ㄦ埛绠＄悊-璐﹀彿鍒濆瀵嗙爜','sys.user.initPassword','123456','Y','admin','2022-05-14 14:04:21','',NULL,'鍒濆鍖栧瘑鐮?123456'),(3,'涓绘鏋堕〉-渚ц竟鏍忎富棰?,'sys.index.sideTheme','theme-dark','Y','admin','2022-05-14 14:04:21','',NULL,'娣辫壊涓婚theme-dark锛屾祬鑹蹭富棰榯heme-light'),(4,'璐﹀彿鑷姪-楠岃瘉鐮佸紑鍏?,'sys.account.captchaOnOff','true','Y','admin','2022-05-14 14:04:21','',NULL,'鏄惁寮€鍚獙璇佺爜鍔熻兘锛坱rue寮€鍚紝false鍏抽棴锛?),(5,'璐﹀彿鑷姪-鏄惁寮€鍚敤鎴锋敞鍐屽姛鑳?,'sys.account.registerUser','false','Y','admin','2022-05-14 14:04:21','',NULL,'鏄惁寮€鍚敞鍐岀敤鎴峰姛鑳斤紙true寮€鍚紝false鍏抽棴锛?);
/*!40000 ALTER TABLE `SYS_CONFIG` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYS_DICT_DATA`
--

DROP TABLE IF EXISTS `SYS_DICT_DATA`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYS_DICT_DATA` (
  `dict_code` bigint NOT NULL AUTO_INCREMENT COMMENT '瀛楀吀缂栫爜',
  `dict_sort` int DEFAULT '0' COMMENT '瀛楀吀鎺掑簭',
  `dict_label` varchar(100) DEFAULT '' COMMENT '瀛楀吀鏍囩',
  `dict_value` varchar(100) DEFAULT '' COMMENT '瀛楀吀閿€?,
  `dict_type` varchar(100) DEFAULT '' COMMENT '瀛楀吀绫诲瀷',
  `css_class` varchar(100) DEFAULT NULL COMMENT '鏍峰紡灞炴€э紙鍏朵粬鏍峰紡鎵╁睍锛?,
  `list_class` varchar(100) DEFAULT NULL COMMENT '琛ㄦ牸鍥炴樉鏍峰紡',
  `is_default` char(1) DEFAULT 'N' COMMENT '鏄惁榛樿锛圷鏄?N鍚︼級',
  `status` char(1) DEFAULT '0' COMMENT '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?,
  `create_by` varchar(64) DEFAULT '' COMMENT '鍒涘缓鑰?,
  `create_time` datetime DEFAULT NULL COMMENT '鍒涘缓鏃堕棿',
  `update_by` varchar(64) DEFAULT '' COMMENT '鏇存柊鑰?,
  `update_time` datetime DEFAULT NULL COMMENT '鏇存柊鏃堕棿',
  `remark` varchar(500) DEFAULT NULL COMMENT '澶囨敞',
  PRIMARY KEY (`dict_code`) USING BTREE,
  KEY `dict_type` (`dict_type`) USING BTREE,
  CONSTRAINT `SYS_DICT_DATA_ibfk_1` FOREIGN KEY (`dict_type`) REFERENCES `SYS_DICT_TYPE` (`dict_type`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=102 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYS_DICT_DATA`
--

LOCK TABLES `SYS_DICT_DATA` WRITE;
/*!40000 ALTER TABLE `SYS_DICT_DATA` DISABLE KEYS */;
INSERT INTO `SYS_DICT_DATA` VALUES (1,1,'鐢?,'0','sys_user_sex','','','Y','0','admin','2022-05-14 14:04:20','',NULL,'鎬у埆鐢?),(2,2,'濂?,'1','sys_user_sex','','','N','0','admin','2022-05-14 14:04:20','',NULL,'鎬у埆濂?),(3,3,'鏈煡','2','sys_user_sex','','','N','0','admin','2022-05-14 14:04:20','',NULL,'鎬у埆鏈煡'),(4,1,'鏄剧ず','0','sys_show_hide','','primary','Y','0','admin','2022-05-14 14:04:20','',NULL,'鏄剧ず鑿滃崟'),(5,2,'闅愯棌','1','sys_show_hide','','danger','N','0','admin','2022-05-14 14:04:20','',NULL,'闅愯棌鑿滃崟'),(6,1,'姝ｅ父','0','sys_normal_disable','','primary','Y','0','admin','2022-05-14 14:04:20','',NULL,'姝ｅ父鐘舵€?),(7,2,'鍋滅敤','1','sys_normal_disable','','danger','N','0','admin','2022-05-14 14:04:20','',NULL,'鍋滅敤鐘舵€?),(8,1,'姝ｅ父','0','sys_job_status','','primary','Y','0','admin','2022-05-14 14:04:20','',NULL,'姝ｅ父鐘舵€?),(9,2,'鏆傚仠','1','sys_job_status','','danger','N','0','admin','2022-05-14 14:04:20','',NULL,'鍋滅敤鐘舵€?),(10,1,'榛樿','DEFAULT','sys_job_group','','','Y','0','admin','2022-05-14 14:04:20','',NULL,'榛樿鍒嗙粍'),(11,2,'绯荤粺','SYSTEM','sys_job_group','','','N','0','admin','2022-05-14 14:04:20','',NULL,'绯荤粺鍒嗙粍'),(12,1,'鏄?,'Y','sys_yes_no','','primary','Y','0','admin','2022-05-14 14:04:20','',NULL,'绯荤粺榛樿鏄?),(13,2,'鍚?,'N','sys_yes_no','','danger','N','0','admin','2022-05-14 14:04:20','',NULL,'绯荤粺榛樿鍚?),(14,1,'閫氱煡','1','sys_notice_type','','warning','Y','0','admin','2022-05-14 14:04:20','',NULL,'閫氱煡'),(15,2,'鍏憡','2','sys_notice_type','','success','N','0','admin','2022-05-14 14:04:20','',NULL,'鍏憡'),(16,1,'姝ｅ父','0','sys_notice_status','','primary','Y','0','admin','2022-05-14 14:04:20','',NULL,'姝ｅ父鐘舵€?),(17,2,'鍏抽棴','1','sys_notice_status','','danger','N','0','admin','2022-05-14 14:04:20','',NULL,'鍏抽棴鐘舵€?),(18,1,'鏂板','1','sys_oper_type','','info','N','0','admin','2022-05-14 14:04:21','',NULL,'鏂板鎿嶄綔'),(19,2,'淇敼','2','sys_oper_type','','info','N','0','admin','2022-05-14 14:04:21','',NULL,'淇敼鎿嶄綔'),(20,3,'鍒犻櫎','3','sys_oper_type','','danger','N','0','admin','2022-05-14 14:04:21','',NULL,'鍒犻櫎鎿嶄綔'),(21,4,'鎺堟潈','4','sys_oper_type','','primary','N','0','admin','2022-05-14 14:04:21','',NULL,'鎺堟潈鎿嶄綔'),(22,5,'瀵煎嚭','5','sys_oper_type','','warning','N','0','admin','2022-05-14 14:04:21','',NULL,'瀵煎嚭鎿嶄綔'),(23,6,'瀵煎叆','6','sys_oper_type','','warning','N','0','admin','2022-05-14 14:04:21','',NULL,'瀵煎叆鎿嶄綔'),(24,7,'寮洪€€','7','sys_oper_type','','danger','N','0','admin','2022-05-14 14:04:21','',NULL,'寮洪€€鎿嶄綔'),(25,8,'鐢熸垚浠ｇ爜','8','sys_oper_type','','warning','N','0','admin','2022-05-14 14:04:21','',NULL,'鐢熸垚鎿嶄綔'),(26,9,'娓呯┖鏁版嵁','9','sys_oper_type','','danger','N','0','admin','2022-05-14 14:04:21','',NULL,'娓呯┖鎿嶄綔'),(27,1,'鎴愬姛','0','sys_common_status','','primary','N','0','admin','2022-05-14 14:04:21','',NULL,'姝ｅ父鐘舵€?),(28,2,'澶辫触','1','sys_common_status','','danger','N','0','admin','2022-05-14 14:04:21','',NULL,'鍋滅敤鐘舵€?),(100,0,'鐧诲綍','1','sys_login_type',NULL,'default',NULL,'0','admin','2022-06-10 00:29:31','admin','2022-06-10 00:29:58',NULL),(101,1,'娉ㄩ攢','0','sys_login_type',NULL,'default',NULL,'0','admin','2022-06-10 00:29:48',NULL,'2022-06-10 00:29:48',NULL);
/*!40000 ALTER TABLE `SYS_DICT_DATA` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYS_DICT_TYPE`
--

DROP TABLE IF EXISTS `SYS_DICT_TYPE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYS_DICT_TYPE` (
  `dict_id` bigint NOT NULL AUTO_INCREMENT COMMENT '瀛楀吀涓婚敭',
  `dict_name` varchar(100) DEFAULT '' COMMENT '瀛楀吀鍚嶇О',
  `dict_type` varchar(100) DEFAULT '' COMMENT '瀛楀吀绫诲瀷',
  `status` char(1) DEFAULT '0' COMMENT '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?,
  `create_by` varchar(64) DEFAULT '' COMMENT '鍒涘缓鑰?,
  `create_time` datetime DEFAULT NULL COMMENT '鍒涘缓鏃堕棿',
  `update_by` varchar(64) DEFAULT '' COMMENT '鏇存柊鑰?,
  `update_time` datetime DEFAULT NULL COMMENT '鏇存柊鏃堕棿',
  `remark` varchar(500) DEFAULT NULL COMMENT '澶囨敞',
  PRIMARY KEY (`dict_id`) USING BTREE,
  UNIQUE KEY `dict_type` (`dict_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYS_DICT_TYPE`
--

LOCK TABLES `SYS_DICT_TYPE` WRITE;
/*!40000 ALTER TABLE `SYS_DICT_TYPE` DISABLE KEYS */;
INSERT INTO `SYS_DICT_TYPE` VALUES (1,'鐢ㄦ埛鎬у埆','sys_user_sex','0','admin','2022-05-14 14:04:20','',NULL,'鐢ㄦ埛鎬у埆鍒楄〃'),(2,'鑿滃崟鐘舵€?,'sys_show_hide','0','admin','2022-05-14 14:04:20','',NULL,'鑿滃崟鐘舵€佸垪琛?),(3,'绯荤粺寮€鍏?,'sys_normal_disable','0','admin','2022-05-14 14:04:20','',NULL,'绯荤粺寮€鍏冲垪琛?),(4,'浠诲姟鐘舵€?,'sys_job_status','0','admin','2022-05-14 14:04:20','',NULL,'浠诲姟鐘舵€佸垪琛?),(5,'浠诲姟鍒嗙粍','sys_job_group','0','admin','2022-05-14 14:04:20','',NULL,'浠诲姟鍒嗙粍鍒楄〃'),(6,'绯荤粺鏄惁','sys_yes_no','0','admin','2022-05-14 14:04:20','',NULL,'绯荤粺鏄惁鍒楄〃'),(7,'閫氱煡绫诲瀷','sys_notice_type','0','admin','2022-05-14 14:04:20','',NULL,'閫氱煡绫诲瀷鍒楄〃'),(8,'閫氱煡鐘舵€?,'sys_notice_status','0','admin','2022-05-14 14:04:20','',NULL,'閫氱煡鐘舵€佸垪琛?),(9,'鎿嶄綔绫诲瀷','sys_oper_type','0','admin','2022-05-14 14:04:20','',NULL,'鎿嶄綔绫诲瀷鍒楄〃'),(10,'绯荤粺鐘舵€?,'sys_common_status','0','admin','2022-05-14 14:04:20','',NULL,'鐧诲綍鐘舵€佸垪琛?),(11,'鐧诲綍鏃ュ織绫诲瀷','sys_login_type','0','admin','2022-06-10 00:28:26','admin','2022-06-10 00:28:26',NULL);
/*!40000 ALTER TABLE `SYS_DICT_TYPE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYUSER`
--

DROP TABLE IF EXISTS `SYUSER`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYUSER` (
  `ID` varchar(36) NOT NULL,
  `AGE` int DEFAULT NULL,
  `CREATEDATETIME` datetime DEFAULT NULL,
  `LOGINNAME` varchar(100) NOT NULL,
  `NAME` varchar(100) DEFAULT NULL,
  `PHOTO` varchar(200) DEFAULT NULL,
  `PWD` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `SEX` varchar(1) DEFAULT NULL,
  `UPDATEDATETIME` datetime DEFAULT NULL,
  `EMPLOYDATE` datetime DEFAULT NULL,
  `EMAIL` varchar(50) DEFAULT '' COMMENT '鐢ㄦ埛閭',
  `PHONENUMBER` varchar(11) DEFAULT '' COMMENT '鎵嬫満鍙风爜',
  `STATUS` varchar(10) DEFAULT '0',
  `SALT` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  PRIMARY KEY (`ID`) USING BTREE,
  UNIQUE KEY `UK_eiov1gsncrds3rean3dmu822p` (`LOGINNAME`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYUSER`
--

LOCK TABLES `SYUSER` WRITE;
/*!40000 ALTER TABLE `SYUSER` DISABLE KEYS */;
INSERT INTO `SYUSER` VALUES ('0',30,'2015-08-25 10:34:54','admin','admin','/system/user/profile/avatar/6ba7f4b1-7935-43d2-baab-64bded5f0106.jpg','!','1','2022-06-08 11:04:52',NULL,'test@test.com','18988888888','0','897149ec9766a98b1b0ae95872080c11'),('0f21b40c-5323-46e5-9200-0364eab3481e',NULL,'2022-05-29 09:28:57','test','test',NULL,'cd4d76879f11122f3034fb24869259fd15963fce3854c2e8355981159856bc30c8e18be9c952b27f1ef728fa8310f6fdfef9a0f1481992a8a5b816e9d59f13ce','0','2022-06-10 09:19:56','2022-05-29 09:28:57','test@test.com','18988888888','0','d53132588025dd85a4a5cc606ff6c711');
/*!40000 ALTER TABLE `SYUSER` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYUSER_SYORGANIZATION`
--

DROP TABLE IF EXISTS `SYUSER_SYORGANIZATION`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYUSER_SYORGANIZATION` (
  `SYUSER_ID` varchar(36) NOT NULL,
  `SYORGANIZATION_ID` varchar(36) NOT NULL,
  PRIMARY KEY (`SYORGANIZATION_ID`,`SYUSER_ID`) USING BTREE,
  KEY `FK_14ewqc5wtscac0dd5rswrm5j2` (`SYORGANIZATION_ID`) USING BTREE,
  KEY `FK_63bdmtxwlk259id13rp4iryy` (`SYUSER_ID`) USING BTREE,
  CONSTRAINT `FK_14ewqc5wtscac0dd5rswrm5j2` FOREIGN KEY (`SYORGANIZATION_ID`) REFERENCES `SYORGANIZATION` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FK_63bdmtxwlk259id13rp4iryy` FOREIGN KEY (`SYUSER_ID`) REFERENCES `SYUSER` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYUSER_SYORGANIZATION`
--

LOCK TABLES `SYUSER_SYORGANIZATION` WRITE;
/*!40000 ALTER TABLE `SYUSER_SYORGANIZATION` DISABLE KEYS */;
INSERT INTO `SYUSER_SYORGANIZATION` VALUES ('0','0'),('0f21b40c-5323-46e5-9200-0364eab3481e','5477d9a9-e41e-485f-bb08-697e8facef88');
/*!40000 ALTER TABLE `SYUSER_SYORGANIZATION` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `SYUSER_SYROLE`
--

DROP TABLE IF EXISTS `SYUSER_SYROLE`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `SYUSER_SYROLE` (
  `SYUSER_ID` varchar(36) NOT NULL,
  `SYROLE_ID` varchar(36) NOT NULL,
  PRIMARY KEY (`SYROLE_ID`,`SYUSER_ID`) USING BTREE,
  KEY `FK_j7iwtgslc2esrjx0ptieleoko` (`SYROLE_ID`) USING BTREE,
  KEY `FK_1pi4p5h4y5ghbs5f4gdlgn620` (`SYUSER_ID`) USING BTREE,
  CONSTRAINT `FK_1pi4p5h4y5ghbs5f4gdlgn620` FOREIGN KEY (`SYUSER_ID`) REFERENCES `SYUSER` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `FK_j7iwtgslc2esrjx0ptieleoko` FOREIGN KEY (`SYROLE_ID`) REFERENCES `SYROLE` (`ID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `SYUSER_SYROLE`
--

LOCK TABLES `SYUSER_SYROLE` WRITE;
/*!40000 ALTER TABLE `SYUSER_SYROLE` DISABLE KEYS */;
INSERT INTO `SYUSER_SYROLE` VALUES ('0','0'),('0','19f00d46-8f1b-45b5-b7b7-6197d7b8cb33'),('0','f4e1b151-a171-4705-9154-503a046cb72a');
/*!40000 ALTER TABLE `SYUSER_SYROLE` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'authbase'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-09 20:41:59
