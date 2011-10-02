----------------------------
The CHIRP Radio Style Guide
----------------------------


Coding Conventions
------------------

In general, Python code should follow the guidelines and conventions
outlined in `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_.

A few additional rules:

* One-character variable names are strongly discouraged, except for
  variables of iteration.
* Avoid "power features" like metaclasses, import hacks, reflection, etc.
  These features are occasionally necessary for low-level hacks in
  core infrastructure, but should generally not occur in applications.
  Simplicity in code is a virtue.
* Code should always be accompanied by unit tests.
* Always use new-style classes by deriving from object in base classes.

Imports
-------

Long lists of imports can be confusing and difficult to scan and
maintain.  To avoid this, the encouraged order to imports is.

* First standard Python modules.
* Then core Django modules.
* Then Google App Engine-specific modules.
* The core chirpradio infrastructure.
* Finally, your application or subcomponent.

Each group of imports should occur in alphabetical order.


Copyright & License Notice
--------------------------

When you create a new source file, please include this notice at the top::

  ###
  ### Copyright [CURRENT YEAR] The Chicago Independent Radio Project
  ### All Rights Reserved.
  ###
  ### Licensed under the Apache License, Version 2.0 (the "License");
  ### you may not use this file except in compliance with the License.
  ### You may obtain a copy of the License at
  ###
  ###     http://www.apache.org/licenses/LICENSE-2.0
  ###
  ### Unless required by applicable law or agreed to in writing, software
  ### distributed under the License is distributed on an "AS IS" BASIS,
  ### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  ### See the License for the specific language governing permissions and
  ### limitations under the License.
  ###

If you edit a file whose copyright year is in the past, do not replace
it with the current year.  The year in a file should reflect the year
that the file was created, not the year it was last edited.


TODO Comments
-------------

In the code, you will occasionally see comments of the form
``# TODO(username): Need to do so-and-so in the future.``

The "username" indicates the person who originally made the note,
*not* the person who is assigned to fix it.  The name is there so that
you can know who to ask if you have questions about the note.

If you are new to the project, a good way to get started is to search
for TODO items and try to do them.
