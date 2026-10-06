import tempfile,unittest
from pathlib import Path
from ccs.common import write_json
from ccs.web import output_readiness
class Readiness(unittest.TestCase):
    def test_media_for_previous_review_is_not_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=Path(tmp);(j/'sermon.mp4').touch();(j/'finished.mp4').touch()
            old=dict(start=10,end=20,title='Old title',date='2026-10-04',passage='Romans 2')
            write_json(j/'media-settings.json',dict(start=10.,duration=10.))
            write_json(j/'validation.json',dict(plan=old,full_decode='passed',audio_channels=1))
            self.assertEqual(output_readiness(j,old,'Finished'),(True,True))
            changed={**old,'title':'New title'}
            self.assertEqual(output_readiness(j,changed,'Finished'),(True,False))
            changed['start']=11
            self.assertEqual(output_readiness(j,changed,'Finished'),(False,False))
            self.assertEqual(output_readiness(j,old,'Rendering'),(False,False))
if __name__=='__main__':unittest.main()
