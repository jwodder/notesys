# This module is an interface between notes.cgi and a SQLite3 database.  If you
# want to use a different kind of database, you need to create & use a separate
# version of this file.

# See the end of the file for a very brief description of the contents of the
# database.

package NoteSys;
use POSIX 'strftime';
use DBI;
use NoteSys::Note;

our $VERSION = v1.0;

sub connect($;%) {
 my %attrs;
 $attrs{db} = DBI->connect("dbi:SQLite:dbname=$_[0]", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
 $attrs{db}->{unicode} = 1;
 $attrs{db}->do('PRAGMA foreign_keys = ON');
 # Prepare frequently used statements:
 $attrs{getTags} = $attrs{db}->prepare('SELECT tag FROM taggings WHERE note=?'
  . ' ORDER BY tag COLLATE NOCASE ASC');
 $attrs{noteById} = $attrs{db}->prepare('SELECT idno, title, contents,'
  . ' strftime("%s", created) AS created, strftime("%s", edited) AS edited,'
  . ' parent FROM notes WHERE idno=?');
 $attrs{getTaggedNotes} = $attrs{db}->prepare('SELECT note FROM taggings'
  . ' WHERE tag=? ORDER BY note DESC');  # ORDER BY notes.created DESC ???
 $attrs{getChildren} = $attrs{db}->prepare('SELECT idno FROM notes'
  . ' WHERE parent=? ORDER BY created DESC');
 $attrs{addTag} = $attrs{db}->prepare('INSERT INTO taggings (note, tag)'
  . ' VALUES (?, ?)');
 $attrs{delTag} = $attrs{db}->prepare('DELETE FROM taggings WHERE note=?'
  . ' AND tag=?');
 bless { %attrs };
}

sub abandon {
 my $self = shift;
 $self->{db}->rollback;
 delete $self->{getTags};
 delete $self->{noteById};
 delete $self->{getTaggedNotes};
 delete $self->{getChildren};
 delete $self->{addTag};
 delete $self->{delTag};
 $self->{db}->disconnect;
 delete $self->{db};
}

sub disconnect {
 my $self = shift;
 $self->{db}->commit;
 # Undefining all of the prepared statement handles seems to be the only way to
 # avoid warnings about closing the database connection "with active statement
 # handles" (No, calling 'finish' on them doesn't work).
 delete $self->{getTags};
 delete $self->{noteById};
 delete $self->{getTaggedNotes};
 delete $self->{getChildren};
 delete $self->{addTag};
 delete $self->{delTag};
 $self->{db}->disconnect;
 delete $self->{db};
}

sub countNotes { ($_[0]{db}->selectrow_array('SELECT COUNT(*) FROM notes'))[0] }

sub countTags {
 ($_[0]{db}->selectrow_array('SELECT COUNT(DISTINCT tag) FROM taggings'))[0]
}

sub fetchNote { # Create the Note object for the given ID
 my($self, $id) = @_;
 my $data = $self->{db}->selectrow_hashref($self->{noteById}, {}, $id);
 return undef if !defined $data;
 my $note = new NoteSys::Note %$data;
 # SQLite3's strftime() function supports only a measly subset of the standard
 # conversion specifications, so timestamp formatting has to be done in Perl:
 $note->created(strftime('%d %b %Y, %H:%M:%S %Z', localtime($note->created)));
 $note->edited(strftime('%d %b %Y, %H:%M:%S %Z', localtime($note->edited)));
 $note->tags($self->{db}->selectcol_arrayref($self->{getTags}, {}, $id));
 return $note;
}

sub getTaggedNoteIDs { # Returns the note IDs with the given tag
 @{$_[0]{db}->selectcol_arrayref($_[0]{getTaggedNotes}, {}, cleanLabel($_[1]))}
}

sub getAllNoteIDs {
 @{$_[0]{db}->selectcol_arrayref(
  'SELECT idno FROM notes ORDER BY created DESC')}
}

sub getChildNoteIDs {
 @{$_[0]{db}->selectcol_arrayref($_[0]{getChildren}, {}, $_[1])}
}

sub updateNote {
 # Rewrite this so that only changed fields are updated.
 my($self, $old, $new) = @_;
 my %oldTags = map { cleanLabel($_) => 0 } $old->tagList;
 for ($new->tagList) {
  my $t = cleanLabel($_);
  if (exists $oldTags{$t}) { $oldTags{$t}++ }
  else { $self->{addTag}->execute($old->idno, $t) }
 }
 while (($tag, $kept) = each %oldTags) {
  $self->{delTag}->execute($old->idno, $tag) if !$kept
 }
 $self->{db}->do('UPDATE notes SET title=?, contents=?,'
  . ' edited=CURRENT_TIMESTAMP WHERE idno=?', {}, cleanLabel($new->title),
  $new->contents, $old->idno);
}

sub deleteNote {
 my($self, $id) = @_;
 $self->{db}->do('DELETE FROM taggings WHERE note=?', {}, $id);
 $self->{db}->do('DELETE FROM notes WHERE idno=?', {}, $id);
}

sub createNote { # Returns the ID of the new note
 my($self, $new) = @_;
 # Should these statements be prepared?
 if (defined $new->created || defined $new->edited) {
  $self->{db}->do('INSERT INTO notes (title, contents, created, edited) VALUES'
   . ' (?, ?, ?, ?)', {}, cleanLabel($new->title), $new->contents,
   $new->created || $new->edited, $new->edited || $new->created)
 } else {
  $self->{db}->do('INSERT INTO notes (title, contents) VALUES (?, ?)', {},
   cleanLabel($new->title), $new->contents)
 }
 my $newid = $self->{db}->last_insert_id(undef, undef, 'notes', undef);
 $self->{addTag}->execute($newid, cleanLabel($_)) for $new->tagList;
 return $newid;
}

sub getTagsAndQtys {
 @{$_[0]{db}->selectall_arrayref('SELECT tag, COUNT(*) FROM taggings GROUP BY'
  . ' tag ORDER BY tag COLLATE NOCASE ASC')}
}

sub create($;%) { # not an instance method
 my $db = DBI->connect("dbi:SQLite:dbname=$_[0]", '', '', {AutoCommit => 0,
  PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;
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

sub getNoteTreeHash {
 # Returns a hash representing the tree of note IDs rooted at the given ID
 my($self, @nodes) = @_;
 my %children;
 while (@nodes) {
  my $n = shift @nodes;
  my @offspring = $self->getChildNoteIDs($n);
  $children{$n} = [ @offspring ];
  push @nodes, @offspring;
 }
 return %children;
}

sub attachNote {
 my($self, $parent, $child) = @_;
 $self->{db}->do('UPDATE notes SET parent=? WHERE idno=?', {}, $parent, $child);
}

sub detachNote {
 $_[0]{db}->do('UPDATE notes SET parent=NULL WHERE idno=?', {}, $_[1])
}

sub topLevelNotes {
 @{$_[0]{db}->selectcol_arrayref('SELECT idno FROM notes WHERE parent=NULL')}
}

sub getInternalDates {
 # Returns the timestamps on the given note as stored internally rather than in
 # the prettified form used by fetchNote
 $_[0]{db}->selectrow_array('SELECT created, edited FROM notes WHERE idno=?',
  {}, $_[1])
 # Should this statement be prepared?
}

sub noteExists {
 ($_[0]{db}->selectrow_array('SELECT EXISTS (SELECT idno FROM notes WHERE'
  . ' idno=?)', {}, $_[1]))[0]
}

sub fetchChildren { map { $_[0]->fetchNote($_) } $_[0]->getChildNoteIDs($_[1]) }

sub cleanLabel($) {
 # called on titles & tags to rid them of undesirable characters
 (my $str = shift) =~ s/\s+/ /g;
 #(my $str = shift) =~ s/[^[:graph:]]+/ /g;
 # ^ This variant is not kind to non-ASCII characters.  Fix this.
 $str =~ s/^\s|\s$//g;
 return $str;
}

1;

__END__

SQLite3 database contents:
 - See createDB() for the actual complete definitions.
 - TABLE notes
  - idno - INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT - note ID
  - title - VARCHAR(255) - note title; make this larger?
  - contents - TEXT - contents of the note
  - created - TIMESTAMP DEFAULT CURRENT_TIMESTAMP - time of creation
  - edited - TIMESTAMP DEFAULT CURRENT_TIMESTAMP - time last edited
  - parent - INTEGER - ID of the parent note, if any; NULL if no parent
 - TABLE taggings
  - note - INTEGER NOT NULL - ID of the note being tagged
  - tag - VARCHAR(255) NOT NULL - tag applied to the note
