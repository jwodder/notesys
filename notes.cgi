#!/usr/bin/perl -wl
use strict;
use CGI qw< :standard start_table start_Tr start_td start_div >;
use CGI::Carp 'fatalsToBrowser';
use NoteSys;

print header, start_html(-title => 'Notes', -head => meta({-http_equiv =>
 'Content-type', -content => 'text/html; charset=UTF-8'}), -style => {-src =>
 'styles.css'});

connect;

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

sub printNote($) {
 my $note = shift;
 print start_div({-style => 'margin-bottom: 2ex'}),
  b(escapeHTML($note->title)), ' &#x2014; ', a({-href => url(-relative => 1) .
  '?edit=' . $note->id}, 'Edit'), ' ', a({-href => url(-relative => 1) .
  '?del=' . $note->id}, 'Delete');
 print $note->contents eq '' ? br : pre(map { escapeHTML "$_\n" }
  map { wrapLine($_, 80) } split /\n/, $note->contents);
 map {
  print a({-href => url(-relative => 1) . '?tag=' . $_->[0]},
   escapeHTML($_->[1])), ' '
 } @{$note->tags};
 # Somewhere in here print 'created', 'edited', and information about parent &
 # child notes.
 print end_div;
}

sub parseTagList($) {
 (my $str = shift) =~ s/^\s+|\s+$//g;
 map { $_ eq '' ? () : getTagByName $_ } split /\s*,\s*/, $str;
}

print start_table({-border => 0, -align => 'center'}), start_Tr,
 start_td({-width => 500});
print p(a({-href => url(-relative => 1)}, 'All items') . ' | '
 . a({-href => url(-relative => 1) . '?new'}, 'New item'));

if (defined url_param('edit')) {
 my $old = fetchNote url_param('edit');
 # Check for errors!
 if (param) {
  my $new = new Note id => $old->id, title => param('title'),
   contents => param('contents'), tags => [ parseTagList param('tags') ];
   # Add in something about the 'parent'?
  updateNote($old, $new);
  print p('Item edited');
 } else {
   print <<EOT
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
EOT
  }
 } else if (isset($_GET['tag'])) {
  map { printNote(fetchNote $_) } getNotesByTag(param('tag'));
   # ORDER BY no DESC
# } else if (isset($_GET['tagname'])) {
#  my $tag = getTabByName param('tagname');
#  map { printNote(fetchNote $_) } getNotesByTag($tag->[0]); # ORDER BY no DESC
 } else if (isset($_GET['new'])) {
  if ($_POST) {
   $tags = tagsToNums($_POST['tags']);
   foreach ($tags as $t) incrementTag($t);
   $cmd = $link->prepare('INSERT INTO todo (title, notes, tags) VALUES (?, ?, ?)');
   /* ^^vv Check return values!!! */
   $cmd->execute(array($_POST['title'], $_POST['notes'], joinTags($tags))) or die ("Error: item creation: " . implode(':', $cmd->errorInfo()));
   echo "<P>Item created</P>";
  } else {
   print <<EOT
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
 } else { map { printNote(fetchNote $_) } getAllNotes } # ORDER BY no DESC

print <<EOT;
<P><A HREF="todo.php">All items</A> | <A HREF="todo.php?new">New item</A></P>
</TD><TD STYLE="font-size: 10px">
<UL>
EOT

 $tags = $link->query('SELECT no, name, qty FROM tags WHERE qty>0 ORDER BY name COLLATE NOCASE ASC');  /* I think 'NOCASE' is an SQLite3 extension. */
 /* Check for errors */
 while ($item = $tags->fetch(PDO::FETCH_NUM)) {
  echo "<LI><A HREF='todo.php?tag=$item[0]'>", htmlspecialchars($item[1]),
   "</A> ($item[2])</LI>";
 }

#print end_ul;

print end_td, end_Tr, end_table;

END {print end_html; $? ? abandon : disconnect; }
