# This module is for using NoteSys with a SQLite3 database.  For other
# databases, use different versions of this file.

package NoteSys;
require Exporter;
our @ISA = ('Exporter');
our $VERSION = v0.1;
our @EXPORT = qw< connect abandon disconnect countNotes countTags fetchNote
 getTaggedNoteIDs getAllNoteIDs getChildNoteIDs updateNote deleteNote
 createNote getTagsAndQtys >;
our @EXPORT_OK = qw< createDB >;
use DBI;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';
my($db, $getTags, $noteById, $getTaggedNotes, $getChildren, $addTag, $delTag);

sub connect() {
 $db = DBI->connect("dbi:SQLite:dbname=$dbfile", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
 $db->{unicode} = 1;
 $db->do('PRAGMA foreign_keys = ON');
 $getTags = $db->prepare('SELECT tag FROM taggings WHERE note=? ORDER BY tag' .
  ' COLLATE NOCASE ASC');
 $noteById = $db->prepare('SELECT idno, title, contents, created, edited,' .
  ' parent FROM notes WHERE idno=?');
 $getTaggedNotes = $db->prepare('SELECT note FROM taggings WHERE tag=?' .
  ' ORDER BY note DESC');
  # ORDER BY notes.created DESC ???
 $getChildren = $db->prepare('SELECT idno FROM notes WHERE parent=?' .
  ' ORDER BY created DESC');
 $addTag = $db->prepare('INSERT INTO taggings (note, tag) VALUES (?, ?)');
 $delTag = $db->prepare('DELETE FROM taggings WHERE note=? AND tag=?');
}

sub abandon() {
 $db->rollback;
 undef $getTags;
 undef $noteById;
 undef $getTaggedNotes;
 undef $getChildren;
 undef $addTag;
 undef $delTag;
 $db->disconnect;
}

sub disconnect() {
 $db->commit;
 # Undefining all of the prepared statement handles seems to be the only way to
 # avoid warnings about closing the database connection "with active statement
 # handles" (No, calling 'finish' on them doesn't work).
 undef $getTags;
 undef $noteById;
 undef $getTaggedNotes;
 undef $getChildren;
 undef $addTag;
 undef $delTag;
 $db->disconnect;
}

sub countNotes() { ($db->selectrow_array('SELECT COUNT(*) FROM notes'))[0] }

sub countTags() {
 ($db->selectrow_array('SELECT COUNT(DISTINCT tag) FROM taggings'))[0]
}

sub fetchNote($) {
 # Create the Note object for the given ID
 my $id = shift;
 my $note = new Note %{$db->selectrow_hashref($noteById, {}, $id)};
 # What should I do when the note doesn't exist?
 $note->tags($db->selectcol_arrayref($getTags, {}, $id));
 return $note;
}

sub getTaggedNoteIDs($) { # Returns the note IDs with the given tag
 @{$db->selectcol_arrayref($getTaggedNotes, {}, $_[0])}
}

sub getAllNoteIDs() {
 @{$db->selectcol_arrayref('SELECT idno FROM notes ORDER BY created DESC')}
}

sub getChildNoteIDs($) { @{$db->selectcol_arrayref($getChildren, {}, $_[0])} }

sub updateNote($$) {
# Rewrite this so that only changed fields are updated.
 my($old, $new) = @_;
 my %oldTags = map { $_ => 0 } @{$old->tags};
 for (@{$new->tags}) {
  if (exists $oldTags{$_}) { $oldTags{$_}++ }
  else { $addTag->execute($old->idno, $_) }
 }
 while (($tag, $kept) = each %oldTags) {
  $delTag->execute($old->idno, $tag) if !$kept
 }
 $db->do('UPDATE notes SET title=?, contents=?, edited=CURRENT_TIMESTAMP' .
  ' WHERE idno=?', {}, $new->title, $new->contents, $old->idno);
}

sub deleteNote($) { # Takes a note ID
 my $id = shift;
 $db->do('DELETE FROM taggings WHERE note=?', {}, $id);
 $db->do('DELETE FROM notes WHERE idno=?', {}, $id);
}

sub createNote($) { # Returns the ID of the new note
 my $new = shift;
 $db->do('INSERT INTO notes (title, contents) VALUES (?, ?)', {}, $new->title,
  $new->contents);
 my $newid = $db->last_insert_id(undef, undef, 'notes', undef);
 $addTag->execute($newid, $_) for @{$new->tags};
 return $newid;
}

sub getTagsAndQtys() {
 @{$db->selectall_arrayref('SELECT tag, COUNT(*) FROM taggings GROUP BY tag' .
  ' ORDER BY tag COLLATE NOCASE ASC')}
}

sub createDB($) {
 $db = DBI->connect("dbi:SQLite:dbname=$_[0]", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
 $db->{unicode} = 1;
 $db->do('PRAGMA foreign_keys = ON');
 $db->do('PRAGMA encoding = "UTF-8"');
 $db->do(q{
  CREATE TABLE notes (idno INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
   title VARCHAR(255) NOT NULL DEFAULT "Untitled", contents TEXT NOT NULL
   DEFAULT "", created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
   edited TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, parent INTEGER
   DEFAULT NULL)
  });
 $db->do(q{
  CREATE TABLE taggings (note INTEGER NOT NULL, tag VARCHAR(255) NOT NULL,
   FOREIGN KEY (note) REFERENCES notes(idno), PRIMARY KEY (note, tag)
   ON CONFLICT IGNORE)
  });
 $db->commit;
 $db->disconnect;
}


package Note;
use Class::Struct idno => '$', title => '$', contents => '$', tags => '@',
 created => '$', edited => '$', parent => '$';

sub children { map { fetchNote $_ } getChildNoteIDs($_[0]->idno) }

1;
