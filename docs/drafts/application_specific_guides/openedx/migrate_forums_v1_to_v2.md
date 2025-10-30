# Overview

This How To documents the process for migrating old style Ruby based v1 OpenEdX forums to the
new Python based v2 forums.

## Process

- Ensure all necessary Forum V2 Settings Are In Place
        - The full list of settings require are detailed
	  [here](https://github.com/openedx/forum)
	- You can find an example of what we did for mitxonline in [this
	  commit](https://github.com/mitodl/ol-infrastructure/blob/main/src/bilder/images/edxapp_v2/templates/edxapp/mitxonline/common_values.yml.tmpl#L345-L364)

- Course Migration Pre-Requisites
        - In order to migrate a course you will need its Course ID. You can find this by
	  navigating to a course in e.g. MITx Online like
	  [this](https://courses.rc.mitxonline.mit.edu/learn/course/course-v1:MITxT+10.50.CH01x+1T2023/home)
	  one. You can extract the course ID by copying the text between course-v1 and 2023.
	  So the course ID here would be `course-v1:MITxT+10.50.CH01x+1T2023`.
- Migrate Course Data
        - You should migrate courses one by one for testing and then once you have the
	  process down migrate all the coursees in a product / environment.
	- You can migrate a simple course by shelling into an LMS container of the product
	  whose course you wish to migrate. Once you're at a bash prompt, you can type:
	  ```
	  ./manage.py lms forum_migrate_course_from_mongodb_to_mysql <course_id_1> <course_id_2>
	  ```
- Enable The Mysql Back-end For This Course
        - Having successfully put the migrated course data in place, we can now enable the
	  mysql backend for this course with the following invocation at the same lms bash
	  shell we used in the previous step:
	  ```
	  ```
