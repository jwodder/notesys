package NoteSys;

# Add in export declarations

use Class::Struct Note => [id => '$', title => '$', contents => '$',
 tags => '@', created => '$', edited => '$', parent => '$'];
# 'id' is the numeric ID of the note.
# 'tags' is a list of tag names.
use DBI;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';

my($link, $tagName, $tagNum, $getTags);

sub connect;
 $link = DBI->connect("dbi:SQLite:dbname=$dbfile", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
 $tagName = $link->prepare('SELECT name FROM tagdata WHERE no=?');
 $tagNum = $link->prepare('SELECT no FROM tagdata WHERE name=?');
 $getTags = $link->prepare('SELECT tag FROM taggings WHERE note=?');
  # Should the tags be sorted somehow?
}

sub getTagID($) { # Get the ID number of a tag
 my $name = shift;
 $tagNum->execute($name);
 my $no = $tagNum->fetchrow_array;
 if (!defined $no) {
  $link->do('INSERT INTO tagdata (name) VALUES (?)', {}, $name);
  $tagNum->execute($name);
  $no = $tagNum->fetchrow_array;
 }
 return $no;
}

my %tagNameCache = ();
sub getTagName($) { # Get the name of a tag based on its ID
 my $no = shift;
 if (exists $tagNameCache{$no}) { return $tagNameCache{$no} }
 else {
  $tagName->execute($no);
  $tagNameCache{$no} = $tagName->fetchrow_array;
  $tagName->finish;
  $tagNameCache{$no} = "TAG_$no" if !defined $tagNameCache{$no};
  return $tagNameCache{$no};
 }
}

sub disconnect;
sub getNoteByID;
sub getNotesByTag;  # Returns a list of notes
sub getAllNotes;
sub countNotes;
sub countTags;
# sub getTagDescription; # ???
sub getChildNotes;  # Get the notes that have the given note ID as a parent
