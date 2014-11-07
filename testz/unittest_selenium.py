# coding: utf-8

import unittest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

class LACSearchUser(unittest.TestCase):

    host = "http://localhost:5000"

    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(4)

    def login(self):
        driver = self.driver
        driver.get("{0}/".format(self.host))
        elem_username = driver.find_element_by_name("username")
        elem_pass  = driver.find_element_by_name("password")
        elem_username.send_keys("chatelain_test")
        elem_pass.send_keys("Sympalecines!")
        driver.find_element_by_id("submit").click()

    def search_by_uidNumber(self):
        driver = self.driver
        driver.get("{0}/search_user".format(self.host))
        #self.assertIn("Recherche de compte", driver.title)
        elem = driver.find_element_by_id("uid_number")
        elem.send_keys("1053")
        driver.find_element_by_id("submit").click()
        assert u"Aucun résultat" not in driver.page_source

    def search_by_sn(self):
        driver = self.driver
        driver.get("{0}/search_user".format(self.host))
        #self.assertIn("Recherche de compte", driver.title)
        elem = driver.find_element_by_id("sn")
        elem.send_keys("chatelain")
        driver.find_element_by_id("submit").click()
        assert u"Aucun résultat" not in driver.page_source



    def search_by_uid(self):
        driver = self.driver
        driver.get("{0}/search_user".format(self.host))
        #self.assertIn("Recherche de compte", driver.title)
        elem = driver.find_element_by_id("uid")
        elem.send_keys("chatelain")
        driver.find_element_by_id("submit").click()
        assert u"Aucun résultat" not in driver.page_source

    def search_by_mail(self):
        driver = self.driver
        driver.get("{0}/search_user".format(self.host))
        #self.assertIn("Recherche de compte", driver.title)
        elem = driver.find_element_by_id("mail")
        elem.send_keys("chatelain@cines.fr")
        driver.find_element_by_id("submit").click()
        assert u"Aucun résultat" not in driver.page_source

    def search_by_user_type(self):
        driver = self.driver
        driver.get("{0}/search_user".format(self.host))
        self.assertIn("Recherche de compte", driver.title)
        elem = Select(driver.find_element_by_id("user_type"))
        elem.select_by_visible_text("Compte CINES")
        driver.find_element_by_id("submit").click()
        assert u"Aucun résultat" not in driver.page_source

    def test_list_group_memberz_cines(self):
        driver = self.driver
        self.login()
        driver.get("{0}/".format(self.host))
        driver.find_element_by_link_text("cines").click()
        assert u"chatelain"  in driver.page_source

    def test_search(self):
        self.search_by_uidNumber(
        self.search_by_sn()
        self.search_by_uid()
        self.search_by_mail(
        self.search_by_user_type()


    def tearDown(self):
        self.driver.close()



if __name__ == "__main__":
    unittest.main()
