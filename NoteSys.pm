# Add in some automatic sorting of notes returned?

# Note: With the exception of 'fetchNote', all functions in NoteSys that deal
# with notes take and return only note IDs.

package NoteSys;

require Exporter;
our @ISA = ('Exporter');
our $VERSION = v0.1;
our @EXPORT = qw< connect abandon disconnect getTagID getTagName countNotes
 countTags fetchNote getNotesByTag getAllNotes getChildNotes >;

use DBI;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';

my($db, $tagName, $tagNum, $getTags, $noteById, $getTaggedNotes, $getChildren);

sub connect() {
 $db = DBI->connect("dbi:SQLite:dbname=$dbfile", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
 $tagName = $db->prepare('SELECT name FROM tagdata WHERE no=?');
 $tagNum = $db->prepare('SELECT no FROM tagdata WHERE name=?');
 $getTags = $db->prepare('SELECT tag FROM taggings WHERE note=?');
  # Should the tags be sorted somehow?
 $noteById = $db->prepare('SELECT no, title, contents, created, edited,' .
  ' parent FROM notes WHERE no=?');
 $getTaggedNotes = $db->prepare('SELECT note FROM taggings WHERE tag=?');
 $getChildren = $db->prepare('SELECT no FROM notes WHERE parent=?');
}

sub abandon() {$db->rollback; $db->disconnect; }
sub disconnect() {$db->commit; $db->disconnect; }

sub getTagID($) { # Get the ID number of a tag
 my $name = shift;
 $tagNum->execute($name);
 my($no) = $tagNum->fetchrow_array;
 if (!defined $no) {
  $db->do('INSERT INTO tagdata (name) VALUES (?)', {}, $name);
  $tagNum->execute($name);
  ($no) = $tagNum->fetchrow_array;
 }
 return $no;
}

my %tagNameCache = ();
sub getTagName($) { # Get the name of a tag based on its ID
 my $no = shift;
 if (exists $tagNameCache{$no}) { return $tagNameCache{$no} }
 else {
  $tagName->execute($no);
  ($tagNameCache{$no}) = $tagName->fetchrow_array;
  $tagName->finish;
  $tagNameCache{$no} = "TAG_$no" if !defined $tagNameCache{$no};
  return $tagNameCache{$no};
 }
}

sub countNotes() { ($db->selectrow_array('SELECT COUNT(*) FROM notes'))[0] }

sub countTags() { ($db->selectrow_array('SELECT COUNT(tag) FROM taggings'))[0] }
 # This SQL statement probably isn't right.

sub fetchNote($) {
 # Create the Note object for the given ID
 my $id = shift;
 my @dat = $db->selectrow_array($noteById, {}, $id);
 # What should I do when the note doesn't exist?
 Note->new(id => $dat[0], title => $dat[1], contents => $dat[2], created =>
  $dat[3], edited => $dat[4], parent => $dat[5], tags =>
  [ map { getTagName $_ } @{$db->selectcol_arrayref($getTags, {}, $id)} ]);
}

sub getNotesByTag($) {
 @{$db->selectcol_arrayref($getTaggedNotes, {}, $_[0])}
 # Returns the notes tagged with the given tag ID
}

sub getAllNotes() { @{$db->selectcol_arrayref('SELECT no FROM notes')} }
sub getChildNotes($) { @{$db->selectcol_arrayref($getChildren, {}, $_[0])} }


package Note;

use Class::Struct id => '$', title => '$', contents => '$', tags => '@',
 created => '$', edited => '$', parent => '$';
# 'id' is the numeric ID of the note.
# 'tags' is a list of tag names.

sub children { map { fetchNote $_ } getChildNotes($_[0]->id) }
