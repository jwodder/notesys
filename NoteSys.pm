package NoteSys;
require Exporter;
our @ISA = ('Exporter');
our $VERSION = v0.1;
our @EXPORT = qw< connect abandon disconnect countNotes countTags fetchNote
 getTaggedNoteIDs getAllNoteIDs getChildNoteIDs updateNote deleteNote
 createNote getTagsAndQtys >;
use DBI;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';
my($db, $getTags, $noteById, $getTaggedNotes, $getChildren, $addTag, $delTag);

sub connect() {
 $db = DBI->connect("dbi:SQLite:dbname=$dbfile", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
 $getTags = $db->prepare('SELECT tag FROM taggings WHERE note=?');
  # Should the tags be sorted somehow?
 $noteById = $db->prepare('SELECT idno, title, contents, created, edited,' .
  ' parent FROM notes WHERE idno=?');
 $getTaggedNotes = $db->prepare('SELECT note FROM taggings WHERE tag=?');
 $getChildren = $db->prepare('SELECT idno FROM notes WHERE parent=?');
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
 new Note idno => $dat[0], title => $dat[1], contents => $dat[2], created =>
  $dat[3], edited => $dat[4], parent => $dat[5],
  tags => $db->selectcol_arrayref($getTags, {}, $id);
}

sub getTaggedNoteIDs($) { # Returns the note IDs with the given tag
 @{$db->selectcol_arrayref($getTaggedNotes, {}, $_[0])}
}

sub getAllNoteIDs() { @{$db->selectcol_arrayref('SELECT idno FROM notes')} }
sub getChildNoteIDs($) { @{$db->selectcol_arrayref($getChildren, {}, $_[0])} }

sub updateNote($$) {
# - Make sure that 'edited' is updated at some point in this function.
# - Rewrite this so that only changed fields are updated.
 my($old, $new) = @_;
 my %oldTags = map { $_ => 0 } $old->tags;
 for ($new->tags) {
  if (exists $oldTags{$_}) { $oldTags{$_}++ }
  else { $addTag->execute($old->idno, $_) }
 }
 while (($tag, $kept) = each %oldTags) {
  $delTag->execute($old->idno, $tag) if !$kept
 }
 $db->do('UPDATE notes SET title=?, contents=? WHERE idno=?', {}, $new->title,
  $new->contents, $old->idno);
}

sub deleteNote($) { # Takes a note ID
 my $id = shift;
 $db->do('DELETE FROM notes WHERE idno=?', {}, $id);
 $db->do('DELETE FROM taggings WHERE note=?', {}, $id);
}

sub createNote($) {
# Make sure that 'created' and 'edited' are set at some point in this function.
 my $new = shift;
 $db->do('INSERT INTO notes (title, contents) VALUES (?, ?)', {}, $new->title,
  $new->contents);
 my $newid = $db->last_insert_id(undef, undef, 'notes', undef);
  # The above line is highly non-portable ... not that this code is likely to
  # ever be ported.
 $addTag->execute($newid, $_) for @{$new->tags};
}

sub getTagsAndQtys() {
 @{$db->selectall_arrayref('SELECT tag, COUNT(note) FROM taggings ORDER BY tag'
  . ' COLLATE NOCASE ASC')}
 # I doubt the above SQL statement is right.  Also, 'NOCASE' might be
 # SQLite3-specific.
}


package Note;
use Class::Struct idno => '$', title => '$', contents => '$', tags => '@',
 created => '$', edited => '$', parent => '$';

sub children { map { fetchNote $_ } getChildNoteIDs($_[0]->idno) }

1;
