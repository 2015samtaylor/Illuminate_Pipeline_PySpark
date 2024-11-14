from .assessments_endpoints import *
from airflow.exceptions import AirflowException
import os
import re



# def add_in_grade_levels(test_results, access_token):

#     #add in grade_level column
#     try:
#         assessments = get_all_assessments_metadata(access_token) 
#         logging.info('Succesfully retrieved all assessments to add in grade levels to test_results frame')
#     except Exception as e:
#         logging.error(f'Unable to get all assessments due to {e}')
#         raise AirflowException(f"Error occurred while getting API token: {e}")

#     grade_levels = assessments[['assessment_id', 'grade_levels']].drop_duplicates()
#     test_results = pd.merge(test_results, grade_levels, on='assessment_id', how='left')
#     test_results = test_results.sort_values(by='date_taken')
#     return(test_results)

def add_in_grade_levels(test_results):
    GL_mapping = pd.read_table('/home/icef/powerschool/Student Rosters.txt')[['STUDENTS.Student_Number', 'STUDENTS.Grade_Level']]
    GL_mapping = GL_mapping.rename(columns={'STUDENTS.Student_Number': 'local_student_id', 
                                            'STUDENTS.Grade_Level': 'grade_levels'})
    GL_mapping['local_student_id'] = GL_mapping['local_student_id'].astype(str)
    test_results = pd.merge(test_results, GL_mapping, on='local_student_id', how='left')
    return(test_results)


#Add in the Curriculum and Unit Columns via string matching from the Assessment Name

def add_in_curriculum_unit_col(df):
    curriculum_dict = {
        'IM': 'IM',
        'Science': 'Science',
        'Into Reading': 'Into Reading',
        'History': 'History',
        'Geometry': 'Geometry',
        'English': 'English',
        'Algebra I': 'Algebra I',
        'Algebra II': 'Algebra II',
        'Algebra 1': 'Algebra I',
        'Algebra 11': 'Algebra II',
        'PreCal': 'Pre-Calculus',
        'Pre Cal': 'Pre-Calculus',
        'Statistics': 'Statistics',
        'Stats': 'Statistics',
        'Biology': 'Biology',
        'Physics': 'Physics',
        'ELA': 'ELA',
        'Math': 'Math',
        'Quantitative': 'Math',
        'Checkpoint': 'Checkpoint'
    }

    # Initialize the Curriculum column with empty strings
    df['curriculum'] = ''

    # Loop through the dictionary to populate the Curriculum column
    for keyword, label in curriculum_dict.items():
        # Use word boundaries only for the 'IM' keyword to match it as a standalone word
        if keyword == 'IM':
            df.loc[df['title'].str.contains(rf'\b{re.escape(keyword)}\b', case=False), 'curriculum'] = label
        else:
            df.loc[df['title'].str.contains(keyword, case=False), 'curriculum'] = label

    # Extract 'Unit', 'Interim', or 'Module' with a number and populate the 'unit' column
    df['unit'] = df['title'].str.extract(r'(Interim(?: Assessment)?(?: #?\d+)?|Interim \d+|Unit \d+|Module \d+)', expand=False)

    #Exception for the IA title standalone, #Remove the assessment and hastag form the unit columns
    df.loc[df['title'].str.contains(rf'\b{re.escape("IA")}\b', case=False), 'unit'] = 'Interim 1'
    df['unit'] = df['unit'].str.replace(r'Assessment|#', '', regex=True).str.strip()
    df['unit'] = df['unit'].str.replace(r'\s+', ' ', regex=True)

    #single interim value in unit needs to align with others
    df['unit'] = df['unit'].replace('Interim', 'Interim 1')

    return df



def create_test_type_column(frame):
    frame['test_type'] = frame['title'].apply(
        lambda x: 'checkpoint' if 'checkpoint' in str(x).lower()
        else 'assessment' if 'assessment' in str(x).lower()
        else 'unknown'
    )
    return frame



def create_test_results_view(test_results, SY):

    test_results = add_in_grade_levels(test_results)
    test_results = add_in_curriculum_unit_col(test_results)

    test_results['year'] = SY

    test_results['test_type'] = ''
    test_results = create_test_type_column(test_results)

    #Cut down cols, and change naming col names
    test_results.loc[:, 'proficiency'] = test_results['performance_band_level'] + ' ' + test_results['performance_band_label'] #add in proficiency column
    test_results = test_results[[ 'assessment_id', 'year', 'date_taken', 'grade_levels', 'local_student_id', 'test_type', 'curriculum', 'unit', 'title', 'standard_code', 'percent_correct', 'performance_band_level', 'performance_band_label', 'proficiency', 'mastered', '__count', 'last_update']]

    test_results = test_results.rename(columns={'grade_levels': 'grade',
                                                'percent_correct': 'score'
                                                  })
    #changes occurs in place
    test_results.loc[test_results['grade'] == 'K', 'grade'] = 0

    test_results = test_results.drop_duplicates()
    
    return(test_results)


def send_to_local(save_path, frame, frame_name):
        
    if not frame.empty:
        frame.to_csv(os.path.join(save_path, frame_name), index=False)
        logging.info(f'{frame_name} saved to {save_path}')
    else:
        logging.info(f'No data present in {frame_name} file')




# Columns unique to test_results_no_standard: {'version', 'version_label'}
# Columns unique to test_results_standard: {'academic_benchmark_guid', 'standard_code', 'standard_description'}

def bring_together_test_results(test_results_no_standard, test_results_standard):

    df = pd.concat([test_results_standard, test_results_no_standard])
    df['standard_code'] = df['standard_code'].fillna('percent')
    df = df.drop_duplicates()

    return(df)