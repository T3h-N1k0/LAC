# coding: utf-8

import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

class LACSearchUser(unittest.TestCase):

    host = "http://host:5000"

    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(10)
        self.admin_login()

    def peon_login(self):
        driver = self.driver
        driver.get("{0}/".format(self.host))
        elem_username = driver.find_element_by_name("username")
        elem_pass  = driver.find_element_by_name("password")
        elem_username.send_keys("chatelain_test")
        elem_pass.send_keys("omgwtfbbqtest!")
        driver.find_element_by_id("submit").click()

    def admin_login(self):
        driver = self.driver
        driver.get("{0}/".format(self.host))
        elem_username = driver.find_element_by_name("username")
        elem_pass  = driver.find_element_by_name("password")
        elem_username.send_keys("chatelain")
        elem_pass.send_keys("omgwtfbbqtest!")
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

    def search_link_to_show(self):
        driver = self.driver
        driver.get("{0}/search_user".format(self.host))
        #self.assertIn("Recherche de compte", driver.title)
        elem = driver.find_element_by_id("uid")
        elem.send_keys("chatelain")
        driver.find_element_by_id("submit").click()
        driver.find_element_by_class_name('odd').click()

    def own_account_view_peon(self):
        driver = self.driver
        driver.get("{0}/show/cines/chatelain".format(self.host))
        self.assertIn(u"Détails pour le compte chatelain", driver.title)

    def own_account_view_admin(self):
        driver = self.driver
        driver.get("{0}/show/cines/chatelain".format(self.host))
        self.assertIn(u"Détails pour le compte chatelain", driver.title)

    def get_edit_account_page(self):
        driver = self.driver
        driver.get("{0}/edit/cines/chatelain".format(self.host))
        self.assertIn(u"Editer le compte chatelain", driver.title)

    def add_account_email(self):
        driver = self.driver
        driver.find_element_by_xpath(
            "//div[@id='mail-fieldset']/button"
        ).click()
        new_mail = driver.find_element_by_id("mail-1")
        new_mail.send_keys("test@test.test")
        driver.find_element_by_id("update").click()

    def check_added_account_email(self):
        driver = self.driver
        driver.get("{0}/show/cines/chatelain".format(self.host))
        assert u"test@test.test"  in driver.page_source

    def del_account_email(self):
        driver = self.driver
        driver.find_element_by_id('mail-1-remove').click()
        driver.find_element_by_id("update").click()

    def check_deleted_account_email(self):
        driver = self.driver
        driver.get("{0}/show/cines/chatelain".format(self.host))
        assert u"test@test.test" not in driver.page_source

    def add_submission(self):
        driver = self.driver
        driver.get("{0}/edit_group_submission/".format(self.host))
        driver.find_element_by_xpath(
            "//select[@id='group_form-available_groupz']/option[text()='cnu0003']"
        ).double_click()
        wrk_group = Select(driver.find_element_by_id(
            "submission_form-wrk_group"
        ))
        wrk_group.select_by_visible_text("ambre")
        driver.find_element_by_id("submission_form-member").click()
        driver.find_element_by_id("submission_form-submission").click()
        driver.find_element_by_id("update").click()
        time.sleep(3)

    def remove_submission(self):
        driver = self.driver
        driver.get("{0}/edit_group_submission/".format(self.host))
        driver.find_element_by_xpath(
            "//select[@id='group_form-available_groupz']/option[text()='cnu0003']"
        ).double_click()
        wrk_group = Select(driver.find_element_by_id(
            "submission_form-wrk_group"
        ))
        wrk_group.select_by_visible_text("ambre")
        driver.find_element_by_id("update").click()
        time.sleep(3)


    def check_added_submission(self):
        driver = self.driver
        driver.get("{0}/show/cines/chatelain".format(self.host))
        assert u"ambre=1" in driver.page_source

    def check_deleted_submission(self):
        driver = self.driver
        driver.get("{0}/show/cines/chatelain".format(self.host))
        assert u"ambre=0" in driver.page_source

    def _test_list_group_memberz_cines(self):
        driver = self.driver
        driver.get("{0}/".format(self.host))
        driver.find_element_by_link_text("cines").click()
        assert u"chatelain"  in driver.page_source

    def _test_search(self):
        self.search_by_uidNumber()
        self.search_by_sn()
        self.search_by_uid()
        self.search_by_mail()
        self.search_by_user_type()
        self.search_link_to_show()

    def _test_show_detailz(self):
        self.own_account_view_admin()

    def _test_edit_account(self):
        self.get_edit_account_page()
        self.add_account_email()
        self.check_added_account_email()
        self.get_edit_account_page()
        self.del_account_email()
        self.check_deleted_account_email()


    def test_edit_group_submission(self):
        self.add_submission()
        self.check_added_submission()
        self.remove_submission()
        self.check_deleted_submission()

    def tearDown(self):
        self.driver.close()



if __name__ == "__main__":
    unittest.main()
