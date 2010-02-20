#!/usr/bin/perl -wl
use strict;
use CGI qw< :standard start_table start_Tr start_td start_div start_ul >;
use CGI::Carp 'fatalsToBrowser';
use Regexp::Common 'URI';
use URI::Escape 'uri_escape_utf8';
use NoteSys qw< :DEFAULT :hier >;

my $dbfile = '/Library/WebServer/Documents/db/notesHier.db';

binmode STDOUT, ':encoding(UTF-8)';

# This whole 'mode' system may be overkill, but it allows the code for
# switching between modes to be neatly encapsulated into one place from which
# it can be easily modified, e.g., to use Apache URL rewriting instead of query
# strings.
use constant {MODE_INTARG => 1, MODE_TEXTARG => 2}; # MODE_INTPAIR => 3
my %modes = (new => 0, back => 0, edit => MODE_INTARG, del => MODE_INTARG,
 tag => MODE_TEXTARG, detach => MODE_INTARG, attach => MODE_INTARG,
 note => MODE_INTARG);
my $mode = url_param('mode');
my $modeArg = url_param('arg');
$mode = 'all' if !defined $mode || !exists $modes{$mode} || $modes{$mode} != 0
 && (!defined $modeArg || $modeArg eq ''
     || $modes{$mode} == MODE_INTARG && $modeArg !~ /^\d+$/
   # || $modes{$mode} == MODE_INTPAIR && $modeArg !~ /^\d+,\d+$/
     );

sub modeLink($;$) {
 my($mode, $arg) = @_;
 return url if $mode eq 'all';
 my $url = url . "?mode=$mode";
 if (defined $arg) { return $url . '&arg=' . uri_escape_utf8($arg) }
 else { return $url }
}

if ($mode eq 'back' || $mode eq 'del' && defined param('decision')
 && param('decision') ne 'Yes') {
 my $last = cookie('lastTag');
 print redirect(defined $last && $last ne '' ? modeLink('tag', $last)
  : modeLink 'all');
 exit(0);
}

my @cookies = ();
if ($mode eq 'all') {
 @cookies = (-cookie => cookie(-name => 'lastTag', -value => ''))
} elsif ($mode eq 'tag') {
 @cookies = (-cookie => cookie(-name => 'lastTag', -value => $modeArg))
}

print header(-type => 'text/html; charset=UTF-8', @cookies), start_html(-title
 => 'Notes', -encoding => 'UTF-8', -declare_xml => 1, -style => {-src =>
 'notes.css'}, -head => Link({-rel => 'icon', -type => 'text/png', -href =>
 'notes.png'}), -script => <<EOJS);
function noteWin(idno) {
 window.open('@{[ url ]}?mode=note&arg=' + idno, 'noteWin');
}
EOJS
# Yes, specifying the encoding twice is necessary so that CGI.pm will send the
# correct headers and so that the in-document charset information agrees with
# said headers.

connectDB $dbfile;

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
 return if !defined $note;
 print start_div({-class => 'noteBlock'}), b(escapeHTML($note->title)); 
 my @utilLinks = ();
 push @utilLinks, a({-href => modeLink('note', $note->idno)}, 'View')
  if $mode ne 'note';
 push @utilLinks, a({-href => modeLink('edit', $note->idno)}, 'Edit')
  if $mode ne 'edit';
 push @utilLinks, a({-href => modeLink('detach', $note->idno)}, 'Detach')
  if defined $note->parent() && $mode ne 'detach';
 push @utilLinks, a({-href => modeLink('attach', $note->idno)}, 'Attach')
  if !defined $note->parent() && $mode ne 'attach';
 push @utilLinks, a({-href => modeLink('del', $note->idno)}, 'Delete')
  if $mode ne 'del';
 print ' ', span({-class => 'editDel'}, join '&nbsp;', @utilLinks);
 print pre(join '',
  map { /$RE{URI}/ ? a({-href => escapeHTML $_}, escapeHTML $_)
   # Is escaping the URL in the HREF necessary and/or desirable?
   : escapeHTML $_ }
  split /($RE{URI})/, join "\n", map { wrapLine($_, 80) } split /\n/,
  $note->contents) if $note->contents ne '';
 print p({-class => 'tags'}, join ', ', map {
  a({-href => modeLink('tag', $_)}, escapeHTML($_))
 } $note->tagList);
 print p({-class => 'timestamp'}, 'Created:', $note->created);
 print p({-class => 'timestamp'}, 'Last edited:', $note->edited)
  if $note->created ne $note->edited;
 print end_div;
}

sub parseTagList($) {
 (my $str = shift) =~ s/^\s+|\s+$//g;
 map { $_ eq '' ? () : $_ } split /\s*,\s*/, $str;
}

print start_table({-border => 0, -align => 'center'}), start_Tr,
 start_td({-width => 500});
print p(a({-href => modeLink 'all'}, 'All notes'), '|',
 a({-href => modeLink 'new'}, 'New note'));

if ($mode eq 'edit') {
 my $old = fetchNote $modeArg;
 if (!defined $old) {
  print p("There is no note #$modeArg....");
  print p(a({-href => modeLink 'back'}, 'Back'));
 } elsif (defined param('title')) {
  my $new = new Note idno => $old->idno, title => param('title'),
   contents => param('contents'), tags => [ parseTagList param('tags') ];
  updateNote($old, $new);
  print p('Note edited'), p(a({-href => modeLink 'back'}, 'Back'));
 } else {
  print start_form(-action => modeLink($mode, $modeArg));
  print textfield('title', $old->title, 80, 255);
  print br, tt(textarea('contents', $old->contents, 10, 80)), br;
  print textfield('tags', join(', ', $old->tagList), 80);
  print br, submit(-value => 'Save'), '&nbsp;' x 20, reset, '&nbsp;' x 20,
   a({-href => modeLink 'back'}, 'Back'), end_form;
 }
} elsif ($mode eq 'tag') {
 my @notes = getTaggedNoteIDs $modeArg;
 if (@notes) { map { printNote(fetchNote $_) } @notes }
 else { print p("There's nothing here.") }
} elsif ($mode eq 'new') {
 if (defined param('title')) {
  createNote(new Note title => param('title'), contents => param('contents'),
   tags => [ parseTagList param('tags') ]);
  print p('Note created'), p(a({-href => modeLink 'back'}, 'Back'));
 } else {
  print start_form(-action => modeLink 'new');
  print textfield('title', '', 80, 255);
  print br, tt(textarea('contents', '', 10, 80)), br;
  print textfield('tags', '', 80);
  print br, submit(-value => 'Save'), '&nbsp;' x 20, a({-href =>
   modeLink 'back'}, 'Back'), end_form;
 }
} elsif ($mode eq 'del') {
 if (defined param('decision') && param('decision') eq 'Yes') {
  if (!noteExists($modeArg)) { print p("There is no note #$modeArg....") }
  else {deleteNote $modeArg; print p('Note deleted'); }
  print p(a({-href => modeLink 'back'}, 'Back'));
 } else {
  my $delee = fetchNote $modeArg;
  if (!defined $delee) {
   print p("There is no note #$modeArg....");
   print p(a({-href => modeLink 'back'}, 'Back'));
  } else {
   print p('Are you sure you want to delete this note?');
   print start_form(-action => modeLink($mode, $modeArg));
   print p(submit('decision', 'Yes'), '&nbsp;' x 20, submit('decision', 'No'));
   print end_form;
   printNote $delee;
    # The 'edit' and/or 'delete' links should probably be omitted when
    # displaying the note here.
  }
 }
} elsif ($mode eq 'attach') {
 if (defined param('parent')) {
  if (param('parent') eq $modeArg) {
   print p("I'm sorry, but this is a Möbius-free zone.")
  } else {
   my $parent = param('parent');
   my $child = $modeArg;
   if (!noteExists($parent)) { print p("There is no note #$parent....") }
   elsif (!noteExists($child)) { print p("There is no note #$child....") }
   else {
    attachNote($parent, $child);
    print p('Note #' . a({-href => modeLink('note', $child)}, $child)
     . ' was attached to note #' . a({-href => modeLink('note', $parent)},
     $parent));
   }
  }
 } else {
  my $orphan = fetchNote $modeArg;
  if (!defined $orphan) { print p("There is no note #$modeArg....") }
  else {
   # Check whether $orphan is currently attached to anything else.
   my @ids = grep { $_ != $modeArg } getAllNoteIDs;
   # Should the note IDs be fetched in a different order than usual?
   if (@ids) {
    print p('What would you like to attach this note to?');
    print start_form(-action => modeLink($mode, $modeArg));
    print popup_menu('parent', \@ids, $ids[0], {
      map { $_ => Note::title fetchNote($_) } @ids
     });
    print p(button(-value => 'View', -onClick =>
     'noteWin(document.getElementsByTagName("select")[0].value);'),
     '&nbsp;' x 20, submit(-value => 'Attach'));
    print end_form;
    printNote $orphan;
   } else { print p("There's nothing to attach to!") }
  }
 }
 print p(a({-href => modeLink 'back'}, 'Back'));
} elsif ($mode eq 'detach') {
 if (!noteExists($modeArg)) { print p("There is no note #$modeArg....") }
 else {
  detachNote $modeArg;
  print p('Note #' . a({-href => modeLink('note', $modeArg)}, $modeArg)
   . ' was detached from its parent note.');
  # Add in a link to $modeArg's former parent.
 }
 print p(a({-href => modeLink 'back'}, 'Back'));
} elsif ($mode eq 'note') {
 my $note = fetchNote $modeArg;
 if (!defined $note) { print p("There is no note #$modeArg....") }
 else {
  printNote $note;
  my @children = $note->children;
  if (@children == 1) {
   print div({-class => 'childQty'}, '1 Child:');
   printNote $children[0];
  } elsif (@children > 1) {
   print div({-class => 'childQty'}, scalar @children . ' Children:');
   printNote $_ for @children;
  }
 }
} else {
 my @notes = getAllNoteIDs;
 if (@notes) { map { printNote(fetchNote $_) } @notes }
 else { print p("There's nothing here.") }
}

print p(a({-href => modeLink 'all'}, 'All notes'), '|',
 a({-href => modeLink 'new'}, 'New note'));

print end_td, start_td({-class => 'tagList'});

my($notes, $tags) = (countNotes, countTags);
print p({-class => 'totals'}, $notes, $notes == 1 ? 'note' : 'notes', '|',
 $tags, $tags == 1 ? 'tag' : 'tags');

print ul(map {
 li(a({-href => modeLink('tag', $_->[0])}, escapeHTML($_->[0])),
  '(' . $_->[1] . ')');
} getTagsAndQtys);

print end_td, end_Tr, end_table, end_html;

END { $? ? abandonDB : disconnectDB }
