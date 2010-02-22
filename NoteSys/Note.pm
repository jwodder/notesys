package NoteSys::Note;
use Class::Struct idno => '$', title => '$', contents => '$', tags => '@',
 created => '$', edited => '$', parent => '$';

use overload '""' => 'idno';
# This ^^ should allow one to pass a Note object instead of a note ID to a
# NoteSys function without any problems.

sub tagList { @{$_[0]->tags} }

1;
