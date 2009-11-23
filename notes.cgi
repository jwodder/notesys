#!/usr/bin/perl -wl
use strict;
use CGI qw< :standard start_table start_tr start_td start_div >;
use DBI;

my $dbfile = '/Library/WebServer/Documents/db/notes.db';

my $style = <<EOT;
pre {font-size: 10px; font-family: monaco, courier, monospace; }
EOT

print header, start_html(-title => 'Notes', -style => {-src => '/styles.css',
 -code => $style}, -head => meta({-http_equiv => 'Content-type',
 -content => 'text/html; charset=UTF-8'}));

my $link = DBI->connect("dbi:SQLite:dbname=$dbfile", '', '', {AutoCommit => 0,
 PrintError => 0, RaiseError => 1}) or die "DBI->connect: " . $DBI::errstr;

my $tagName = $link->prepare('SELECT name FROM tagdata WHERE no=?');
my $tagNum = $link->prepare('SELECT no FROM tagdata WHERE name=?');
my $getTags = $link->prepare('SELECT tag FROM taggings WHERE note=?');
 # Should the tags be sorted somehow?

sub wrapLine($;$) {
 my $str = shift;
 my $len = shift || 80;
 $str =~ s/\s+$//;
 my @lines = ();
 while (length $str > $len) {
  if (reverse(substr $str, 0, $len) =~ /\s+/) {
   push @lines, substr $str, 0, $len - $+[0], ''
  } else { push @lines, substr $str, 0, $len, '' }
  $str =~ s/^\s+//;
 }
 return (@lines, $str);
}

my %tagNameCache = ();
sub getTagName($) {
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

sub listToDos($) {
 my $rows = shift;
 while (my @item = $rows->fetchrow_array) {
  print start_div({-style => 'margin-bottom: 2ex'}), b(escapeHTML($item[1])),
   ' &#x2014; ', a({-href => url(-relative => 1) . "?edit=$item[0]"}, 'Edit'),
   ' ', a({-href => url(-relative => 1) . "?del=item[0]"}, 'Delete');
  print $item[2] eq '' ? br : pre(map { escapeHTML "$_\n" }
   map { wrapLine($_, 80) } split /\n/, $item[2]);
  $getTags->execute($item[0]);
  while (my @t = $getTags->fetchrow_array) {
   print a({-href => url(-relative => 1) . "?tag=$t[0]"},
    escapeHTML(getTagName($t[0]))), ' ';
  }
  print end_div;
 }
}

sub getTagNum($) {
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

#sub purgeZeroTags() {
# $link->do('DELETE FROM tagdata WHERE qty <= 0');
#}

sub tagsToNums($) {
 (my $str = shift) =~ s/^\s+|\s+$//g;
 $str =~ s/\s+/ /g;
 map { $_ eq '' ? () : getTagNum $_ } split / ?, ?/, $str;
}


print start_table({-border => 0, -align => 'center'}), start_tr,
 start_td({-width => 500});
print p(a({-href => url(-relative => 1)}, 'All items') . ' | '
 . a({-href => url(-relative => 1) . '?new'}, 'New item'));


 if (isset($_GET['edit'])) {
  $old = $link->query('SELECT * FROM todo WHERE no=' . (int) $_GET['edit']);
  /* Check for errors! */
  $todo = $old->fetch(PDO::FETCH_ASSOC);
  $old = NULL;
  if ($_POST) {
   $oldTags = array();
   foreach (splitTags($todo['tags']) as $t) $oldTags[$t] = 0;
   $newTags = tagsToNums($_POST['tags']);
   foreach ($newTags as $t) {
    if (array_key_exists($t, $oldTags)) $oldTags[$t]++;
    else incrementTag($t);
   }
   foreach ($oldTags as $t => $b) if (!$b) decrementTag($t);
   purgeZeroTags();
   // Modify this so that it only updates fields that changed
   $cmd = $link->prepare('UPDATE todo SET title=?, notes=?, tags=? where no=?');
   // ^^vv Check return values!!!
   $cmd->execute(array($_POST['title'], $_POST['notes'], joinTags($newTags), (int) $_GET['edit'])) or die("Error: editing item: " . implode(':', $cmd->errorInfo()));
   echo "<P>Item edited</P>";
  } else {
   echo <<<EOT
<FORM METHOD="POST" ACTION="?edit={$_GET['edit']}">
<!-- TO DO: Perform escaping on the VALUEs -->
<INPUT TYPE="TEXT" NAME="title" MAXLENGTH="80" SIZE="80" VALUE="{$todo['title']}">
<BR>
<TT><TEXTAREA NAME="notes" COLS="80" ROWS="6">{$todo['notes']}</TEXTAREA></TT>
<BR>
<INPUT TYPE="TEXT" NAME="tags" MAXLENGTH="255" SIZE="80" VALUE="
EOT;
   echo implode(' ', array_map('getTagName', splitTags($todo['tags'])));
   echo <<<EOT
">
<BR>
<INPUT TYPE="SUBMIT" VALUE="Submit">
</FORM>
EOT;
  }
 } else if (isset($_GET['tag'])) {
  listToDos($link->query('SELECT no, title, notes, tags FROM todo WHERE tags LIKE "% ' . (int) $_GET['tag'] . ' %" ORDER BY no DESC'));
 } else if (isset($_GET['new'])) {
  if ($_POST) {
   $tags = tagsToNums($_POST['tags']);
   foreach ($tags as $t) incrementTag($t);
   $cmd = $link->prepare('INSERT INTO todo (title, notes, tags) VALUES (?, ?, ?)');
   /* ^^vv Check return values!!! */
   $cmd->execute(array($_POST['title'], $_POST['notes'], joinTags($tags))) or die ("Error: item creation: " . implode(':', $cmd->errorInfo()));
   echo "<P>Item created</P>";
  } else {
   echo <<<EOT
<FORM METHOD="POST" ACTION="?new">
<INPUT TYPE="TEXT" NAME="title" MAXLENGTH="80" SIZE="80">
<BR>
<TT><TEXTAREA NAME="notes" COLS="80" ROWS="6"></TEXTAREA></TT>
<BR>
<INPUT TYPE="TEXT" NAME="tags" MAXLENGTH="255" SIZE="80">
<BR>
<INPUT TYPE="SUBMIT" VALUE="Submit">
</FORM>
EOT;
  }
 } else if (isset($_GET['del'])) {
  $tags = $link->query('SELECT tags FROM todo WHERE no=' . (int) $_GET['del']);
  foreach (splitTags($tags->fetchColumn()) as $t) decrementTag($t);
  purgeZeroTags();
  $link->exec('DELETE FROM todo WHERE no=' . (int) $_GET['del']);
  /* Check return value? */
  echo "<P>Item deleted</P>";
 } else {
  /* Basic retrieval of all To-Dos */
  listToDos($link->query('SELECT no, title, notes, tags FROM todo ORDER BY no DESC'));
 }
?>
<P><A HREF="todo.php">All items</A> | <A HREF="todo.php?new">New item</A></P>
</TD><TD STYLE="font-size: 10px">
<UL>
<?PHP
 $tags = $link->query('SELECT no, name, qty FROM tags WHERE qty>0 ORDER BY name COLLATE NOCASE ASC');  /* I think 'NOCASE' is an SQLite3 extension. */
 /* Check for errors */
 while ($item = $tags->fetch(PDO::FETCH_NUM)) {
  echo "<LI><A HREF='todo.php?tag=$item[0]'>", htmlspecialchars($item[1]),
   "</A> ($item[2])</LI>";
 }
?>
</UL>
</TD></TR></TABLE>
</BODY>
</HTML>


__END__

To do:
 - Insert lots of error & return value checking!
 - Deal with HTML-encoding & quote-escaping of text in forms
 - Add styles to everything
  - Get the TEXTAREA contents to actually be monospaced?
 - Enforce the 32-character limit for tag names & the 255-character limit for
   the tag number string
 - Process POSTed tag names case-insensitively
 - Implement hierarchic to-do items?
 - Create a special tag for tagless items?
 - Add a "reset" button to the "edit item" page

Database tables:
 - notes
  - no - INTEGER PRIMARY KEY AUTO_INCREMENT
  - title - VARCHAR(255)
  - contents - TEXT
  /*- tags - VARCHAR(255)*/
 - tagdata
  - no - INTEGER PRIMARY KEY AUTO_INCREMENT
  - name - VARCHAR(255)
  /*- qty - INT DEFAULT 0*/
 - taggings
  - note - INTEGER - number of the item being tagged
  - tag - INTEGER - number of the tag assigned
 - Remove the underscore in 'AUTO_INCREMENT' when using sqlite3 instead of
   MySQL (look into this more)
