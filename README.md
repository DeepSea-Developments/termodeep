# Termodeep

File recommended location: `/opt/termodeep`

Recommended to use with supervisord

Main database location: `/database_v2.db`

## Commands

Stop termodeep

    sudo supervisorctl stop termodeep

Start termodeep

    sudo supervisorctl start termodeep
    
Restart termodeep

    sudo superviorctl restart termodeep
    
# Versions description

## version 1.4.1

- Improve database crash from version 1.4.1
- Jquery's Datatable can be use with filters and it work correctly

## Version 1.4
### Features

- Improved front. Files are now more organized
- Implemented Jinja templates
- Implementation of jquery datatables

### Known bugs

1. DataTable crash if database is too large
1. Person information is not always erased from the screen

