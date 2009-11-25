# Add in some automatic sorting of notes returned?

# Note: With the exception of 'fetchNote' and 'updateNote', all functions in
# NoteSys that deal with notes take and return only note IDs.

package NoteSys;

require Exporter;
our @ISA = ('Exporter');
our $VERSION = v0.1;
our @EXPORT = qw< connect abandon disconnect countNotes countTags fetchNote
 getNotesByTag getAllNotes getChildNotes updateNote >;

use DBI;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';

my($db, $getTags, $noteById, $getTaggedNotes, $getChildren, $addTag, $delTag);

sub connect() {
 $db = DBI->connect("dbi:SQLite:dbname=$dbfile", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
 $getTags = $db->prepare('SELECT tag FROM taggings WHERE note=?');
  # Should the tags be sorted somehow?
 $noteById = $db->prepare('SELECT no, title, contents, created, edited,' .
  ' parent FROM notes WHERE no=?');
 $getTaggedNotes = $db->prepare('SELECT note FROM taggings WHERE tag=?');
 $getChildren = $db->prepare('SELECT no FROM notes WHERE parent=?');
 $addTag = $db->prepare('INSERT INTO taggings (note, tag) VALUES (?, ?)');
 $delTag = $db->prepare('DELETE FROM taggings WHERE note=? AND tag=?');
}

sub abandon() {$db->rollback; $db->disconnect; }
sub disconnect() {$db->commit; $db->disconnect; }

sub countNotes() { ($db->selectrow_array('SELECT COUNT(*) FROM notes'))[0] }

sub countTags() { ($db->selectrow_array('SELECT COUNT(tag) FROM taggings'))[0] }
 # This SQL statement probably isn't right.

sub fetchNote($) {
 # Create the Note object for the given ID
 my $id = shift;
 my @dat = $db->selectrow_array($noteById, {}, $id);
 # What should I do when the note doesn't exist?
 new Note id => $dat[0], title => $dat[1], contents => $dat[2], created =>
  $dat[3], edited => $dat[4], parent => $dat[5],
  tags => $db->selectcol_arrayref($getTags, {}, $id);
}

sub getNotesByTag($) { # Returns the notes tagged with the given tag
 @{$db->selectcol_arrayref($getTaggedNotes, {}, $_[0])}
}

sub getAllNotes() { @{$db->selectcol_arrayref('SELECT no FROM notes')} }
sub getChildNotes($) { @{$db->selectcol_arrayref($getChildren, {}, $_[0])} }

sub updateNote($$) {
# - Make sure that 'edited' is updated at some point in this function.
# - Rewrite this so that only changed fields are updated.
# - Somewhere (not necessarily in this function) delete tags that are no longer
#   used.
 my($old, $new) = @_;
 my %oldTags = map { $_ => 0 } $old->tags;
 for ($new->tags) {
  if (exists $oldTags{$_}) { $oldTags{$_}++ }
  else { $addTag->execute($old->id, $_) }
 }
 while (($tag, $kept) = each %oldTags) {
  $delTag->execute($old->id, $tag) if !$kept
 }
 $db->do('UPDATE notes SET title=?, contents=? WHERE no=?', {}, $new->title,
  $new->contents, $old->id);
}

sub createNote($);
sub getTagQty($);
sub deleteNote($);  # Takes a note ID
sub getTagsAndQtys();  # ORDER BY tag COLLATE NOCASE ASC -- 'NOCASE' might be SQLite3-specific


package Note;
use Class::Struct id => '$', title => '$', contents => '$', tags => '@',
 created => '$', edited => '$', parent => '$';

sub children { map { fetchNote $_ } getChildNotes($_[0]->id) }
