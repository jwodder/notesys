#!/usr/bin/perl -wl
use strict;
use CGI qw< :standard start_table start_Tr start_td start_div start_ul >;
use CGI::Carp 'fatalsToBrowser';
use Regexp::Common 'URI';
use URI::Escape 'uri_escape_utf8';
use NoteSys;
use NoteSys::Note;

my $dbfile = '/Library/WebServer/Documents/db/notesHier.db';
my $db;

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
   # || $modes{$mode} == MODE_INTPAIR && $modeArg !~ /^\d+,\d+$/
     || $modes{$mode} == MODE_INTARG && $modeArg !~ /^\d+$/);

### Beginning of subroutine definitions ###

sub modeLink($;$) {
 my($mode, $arg) = @_;
 return url if $mode eq 'all';
 my $url = url . "?mode=$mode";
 if (defined $arg) { return $url . '&arg=' . uri_escape_utf8($arg) }
 else { return $url }
}

sub preamble(;$$) {
 my($subtitle, $autoback) = @_;
 my @cookies = ();
 if ($mode eq 'all') {
  @cookies = (-cookie => cookie(-name => 'lastTag', -value => ''))
 } elsif ($mode eq 'tag') {
  @cookies = (-cookie => cookie(-name => 'lastTag', -value => $modeArg))
 }
 my @head = (Link({-rel => 'icon', -type => 'text/png', -href => 'notes.png'}));
 push @head, meta({-http_equiv => 'Refresh', -content => '5;url='
  . modeLink('back')}) if $autoback;
 print header(-type => 'text/html; charset=UTF-8', @cookies), start_html(-title
  => defined $subtitle ? "NoteSys \x{2014} $subtitle" : 'NoteSys',
   # CGI.pm auto-escapes the contents of the title.
  -encoding => 'UTF-8', -declare_xml => 1, -style => {-src => 'notes.css'},
   # Yes, specifying the encoding twice is necessary so that CGI.pm will send
   # the correct headers and so that the in-document charset information agrees
   # with said headers.
  -head => [ @head ], -script => <<EOJS);
function noteWin(idno) {
 window.open('@{[ url ]}?mode=note&arg=' + idno, 'noteWin');
}
EOJS
 print start_table({-border => 0, -align => 'center'}), start_Tr,
  start_td({-width => 500});
 print p(a({-href => modeLink 'all'}, 'All notes'), '|',
  a({-href => modeLink 'new'}, 'New note'));
}

sub wrapLines($;$) {
 my $str = shift;
 my $len = shift || 80;
 $str =~ s/\s+$//;
 map {
  my @lines = ();
  while (length > $len && /\s+/) {
   if (reverse (substr $_, 0, $len + 1) =~ /\s+/) {
    # Adding one to the length causes a space immediately after the first $len
    # characters to be taken into account.
    push @lines, substr $_, 0, $len + 1 - $+[0], ''
   } else { /\s+/ && push @lines, substr $_, 0, $-[0], '' }
   s/^\s+//;
  }
  if ($_ ne '') { (@lines, $_) }
  else { @lines }
 } split /\n/, $str;
}

sub printNote($) {
 my $note = shift;
 return if !defined $note;
 print start_div({-class => 'noteBlock'}), b(escapeHTML($note->title)); 
 my @utilLinks = ();
 push @utilLinks, a({-href => modeLink('note', $note->idno)}, 'View')
  unless $mode eq 'note' && $modeArg == $note->idno;
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
  map { /$RE{URI}/ ? a({-href => $_}, escapeHTML $_) : escapeHTML $_ }
   # CGI.pm escapes the HREF attribute automatically.
  split /($RE{URI})/, join "\n", map { wrapLines($_, 80) } $note->contents)
  if $note->contents ne '';
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

### End of subroutine definitions ###

if ($mode eq 'back' || $mode eq 'del' && defined param('decision')
 && param('decision') ne 'Yes') {
 my $last = cookie('lastTag');
 print redirect(defined $last && $last ne '' ? modeLink('tag', $last)
  : modeLink 'all');
} else {
 $db = NoteSys::connect $dbfile;
 # If connecting to the database fails here before `preamble' is called,
 # CGI::Carp will still print the HTTP headers appropriately (though without a
 # good <title>).
 if ($mode eq 'edit') {
  my $old = $db->fetchNote($modeArg);
  if (!defined $old) {
   preamble 'No such note';
   print p("There is no note #$modeArg....");
   print p(a({-href => modeLink 'back'}, 'Back'));
  } elsif (defined param('title')) {
   preamble 'Note edited', 1;
   my $new = new NoteSys::Note idno => $old->idno, title => param('title'),
    contents => param('contents'), tags => [ parseTagList param('tags') ];
   $db->updateNote($old, $new);
   print p('Note edited'), p(a({-href => modeLink 'back'}, 'Back'));
  } else {
   preamble('Editing "' . $old->title . '"');
   print start_form(-action => modeLink($mode, $modeArg));
   print textfield('title', $old->title, 80, 255);
   print br, tt(textarea('contents', $old->contents, 10, 80)), br;
   print textfield('tags', join(', ', $old->tagList), 80);
   print br, submit(-value => 'Save'), '&nbsp;' x 20, reset, '&nbsp;' x 20,
    a({-href => modeLink 'back'}, 'Back'), end_form;
  }
 } elsif ($mode eq 'tag') {
  preamble "Notes tagged \"$modeArg\"";
  my @notes = $db->getTaggedNoteIDs($modeArg);
  if (@notes) { map { printNote $db->fetchNote($_) } @notes }
  else { print p("There's nothing here.") }
 } elsif ($mode eq 'new') {
  if (defined param('title')) {
   preamble 'Note created', 1;
   $db->createNote(new NoteSys::Note title => param('title'), contents =>
    param('contents'), tags => [ parseTagList param('tags') ]);
   print p('Note created'), p(a({-href => modeLink 'back'}, 'Back'));
  } else {
   preamble 'New';
   print start_form(-action => modeLink 'new');
   print textfield('title', '', 80, 255);
   print br, tt(textarea('contents', '', 10, 80)), br;
   print textfield('tags', '', 80);
   print br, submit(-value => 'Save'), '&nbsp;' x 20, a({-href =>
    modeLink 'back'}, 'Back'), end_form;
  }
 } elsif ($mode eq 'del') {
  if (defined param('decision') && param('decision') eq 'Yes') {
   if (!$db->noteExists($modeArg)) {
    preamble 'No such note';
    print p("There is no note #$modeArg....");
   } else {
    preamble 'Note deleted', 1;
    $db->deleteNote($modeArg);
    print p('Note deleted');
   }
   print p(a({-href => modeLink 'back'}, 'Back'));
  } else {
   my $delee = $db->fetchNote($modeArg);
   if (!defined $delee) {
    preamble 'No such note';
    print p("There is no note #$modeArg....");
    print p(a({-href => modeLink 'back'}, 'Back'));
   } else {
    preamble 'Delete?';
    print p('Are you sure you want to delete this note?');
    print start_form(-action => modeLink($mode, $modeArg));
    print p(submit('decision', 'Yes'), '&nbsp;' x 20, submit('decision', 'No'));
    print end_form;
    printNote $delee;
   }
  }
 } elsif ($mode eq 'attach') {
  if (defined param('parent')) {
   if (param('parent') eq $modeArg) {
    preamble 'Infinite loop detected';
    print p("I'm sorry, but this is a Möbius-free zone.")
   } else {
    my $parent = param('parent');
    my $child = $modeArg;
    if (!$db->noteExists($parent)) {
     preamble 'No such note';
     print p("There is no note #$parent....");
    } elsif (!$db->noteExists($child)) {
     preamble 'No such note';
     print p("There is no note #$child....");
    } else {
     preamble 'Attached', 1;
     $db->attachNote($parent, $child);
     print p('Note #' . a({-href => modeLink('note', $child)}, $child)
      . ' was attached to note #' . a({-href => modeLink('note', $parent)},
      $parent));
    }
   }
  } else {
   my $orphan = $db->fetchNote($modeArg);
   if (!defined $orphan) {
    preamble 'No such note';
    print p("There is no note #$modeArg....");
   } else {
    preamble 'Attaching';
    # Check whether $orphan is currently attached to anything else.
    my @ids = grep { $_ != $modeArg } $db->getAllNoteIDs;
    # Should the note IDs be fetched in a different order than usual?
    if (@ids) {
     print p('What would you like to attach this note to?');
     print start_form(-action => modeLink($mode, $modeArg));
     print popup_menu('parent', \@ids, $ids[0], {map {
       my $title = $db->fetchNote($_)->title;
       if (length $title > 40) { $_ => substr($title, 0, 40) . "\x{2026}" }
       else { $_ => $title }
      } @ids});
     print p(submit(-value => 'Attach'), '&nbsp;' x 20, button(-value => 'View',
      -onClick =>
       'noteWin(document.getElementsByTagName("select")[0].value);'));
     print end_form;
     printNote $orphan;
    } else { print p("There's nothing to attach to!") }
   }
  }
  print p(a({-href => modeLink 'back'}, 'Back'));
 } elsif ($mode eq 'detach') {
  if (!$db->noteExists($modeArg)) {
   preamble 'No such note';
   print p("There is no note #$modeArg....");
  } else {
   preamble 'Detached', 1;
   $db->detachNote($modeArg);
   print p('Note #' . a({-href => modeLink('note', $modeArg)}, $modeArg)
    . ' was detached from its parent note.');
   # Add in a link to $modeArg's former parent.
  }
  print p(a({-href => modeLink 'back'}, 'Back'));
 } elsif ($mode eq 'note') {
  my $note = $db->fetchNote($modeArg);
  if (!defined $note) {
   preamble 'No such note';
   print p("There is no note #$modeArg....");
  } else {
   preamble $note->title;
   printNote $note;
   my @children = $db->getChildren($note->idno);
   if (@children == 1) {
    print div({-class => 'childQty'}, '1 Child:');
    printNote $children[0];
   } elsif (@children > 1) {
    print div({-class => 'childQty'}, scalar @children . ' Children:');
    printNote $_ for @children;
   }
  }
 } else {
  preamble;
  my @notes = $db->getAllNoteIDs;
  if (@notes) { map { printNote $db->fetchNote($_) } @notes }
  else { print p("There's nothing here.") }
 }
 print p(a({-href => modeLink 'all'}, 'All notes'), '|',
  a({-href => modeLink 'new'}, 'New note'));
 print end_td, start_td({-class => 'tagList'});
 my($notes, $tags) = ($db->countNotes, $db->countTags);
 print p({-class => 'totals'}, $notes, $notes == 1 ? 'note' : 'notes', '|',
  $tags, $tags == 1 ? 'tag' : 'tags');
 print start_ul;
 print li(a({-href => modeLink('tag', $_->[0])}, escapeHTML($_->[0])),
  '(' . $_->[1] . ')') for $db->getTagsAndQtys;
 print end_ul, end_td, end_Tr, end_table, end_html;
}

END { $? ? $db->abandon : $db->disconnect if defined $db }
