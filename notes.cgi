#!/usr/bin/perl -wl
use strict;
use CGI qw< :standard start_table start_Tr start_td start_div start_ul >;
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
  '?edit=' . $note->idno}, 'Edit'), ' ', a({-href => url(-relative => 1) .
  '?del=' . $note->idno}, 'Delete');
 print $note->contents eq '' ? br : pre(map { escapeHTML "$_\n" }
  map { wrapLine($_, 80) } split /\n/, $note->contents);
 print join ', ', map {
  a({-href => url(-relative => 1) . '?tag=' . $_}, escapeHTML($_))
  # The tag name in the query string NEEDS to be escaped!
 } @{$note->tags};
 # Somewhere in here print 'created', 'edited', and information about parent &
 # child notes.
 print end_div;
}

sub parseTagList($) {
 (my $str = shift) =~ s/^\s+|\s+$//g;
 map { $_ eq '' ? () : $_ } split /\s*,\s*/, $str;
}

print start_table({-border => 0, -align => 'center'}), start_Tr,
 start_td({-width => 500});
print p({-style => 'font-size: 10px'}, countNotes, 'notes |', countTags,
 'tags');
print p(a({-href => url(-relative => 1)}, 'All items') . ' | '
 . a({-href => url(-relative => 1) . '?new'}, 'New item'));

if (defined url_param('edit')) {
 my $old = fetchNote url_param('edit');
 # Check for errors!
 if (param) {
  my $new = new Note idno => $old->idno, title => param('title'),
   contents => param('contents'), tags => [ parseTagList param('tags') ];
  # Add in something for the 'parent'?
  updateNote($old, $new);
  print p('Note edited');
 } else {
  print start_form(-action => url(-relative => 1) . '?edit=' . $old->idno);
  print textfield('title', $old->title, 80, 255);
  print br, tt(textarea('contents', $old->contents, 6, 80)), br;
  print textfield('tags', join(', ', @{$old->tags}), 80, 255);
  print br, submit(-value => 'Submit'), end_form;
 }
} elsif (defined url_param('tag')) {
 map { printNote(fetchNote $_) } getTaggedNoteIDs(url_param('tag'))
  # ORDER BY no DESC
} elsif (defined url_param('new')) {
 if (param) {
  createNote(new Note title => param('title'), contents => param('contents'),
   tags => [ parseTagList param('tags') ]);
  print p('Note created');
 } else {
  print start_form(-action => url(-relative => 1) . '?new');
  print textfield('title', '', 80, 255);
  print br, tt(textarea('contents', '', 6, 80)), br;
  print textfield('tags', '', 80, 255);
  print br, submit(-value => 'Submit'), end_form;
 }
} elsif (defined url_param('del')) {
 deleteNote(url_param('del'));
 print p('Note deleted');
} else { map { printNote(fetchNote $_) } getAllNoteIDs } # ORDER BY no DESC

print p(a({-href => url(-relative => 1)}, 'All notes') . ' | '
 . a({-href => url(-relative => 1) . '?new'}, 'New note'));
print end_td, start_td({-style => 'font-size: 10px'});

print ul(map {
 li(a({-href => url(-relative => 1) . '?tag=' . $_->[0]}, escapeHTML($_->[0]))
 # The tag name in the query string NEEDS to be escaped!
  . ' (' . $_->[1] . ')');
} getTagsAndQtys);

print end_td, end_Tr, end_table;

END {print end_html; $? ? abandon : disconnect; }
