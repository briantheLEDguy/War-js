// Unsaved native fixtures only. No real Content loads, asset registration, package saves or art approval.
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarMageReviewLibrary.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Engine/SkeletalMesh.h"
#include "ReferenceSkeleton.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Async/Async.h"
#include <limits>

namespace WarMageReviewTests
{
constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter;

FString NewCandidateRoot()
{
    return TEXT("/Game/Characters/MageFaceDiagnostic/automation_") +
        FGuid::NewGuid().ToString(EGuidFormats::Digits).ToLower();
}

UPackage* FixturePackage(const FString& Root, const TCHAR* Name)
{
    // CreatePackage is in-memory here; transient flags exclude fixtures from persistence.
    UPackage* Package = CreatePackage(*(Root + TEXT("/") + Name));
    Package->SetFlags(RF_Transient);
    return Package;
}

USkeleton* Skeleton(const FString& Root, const TCHAR* Name, FName HeadName=TEXT("head"),
    int32 HeadParent=1, FTransform HeadPose=FTransform(FVector(0,0,25)))
{
    USkeleton* Result = NewObject<USkeleton>(FixturePackage(Root,Name), FName(Name), RF_Transient | RF_Transactional);
    {
        FReferenceSkeletonModifier Modifier(Result);
        Modifier.Add(FMeshBoneInfo(TEXT("root"),TEXT("root"),INDEX_NONE), FTransform::Identity);
        Modifier.Add(FMeshBoneInfo(TEXT("neck"),TEXT("neck"),0), FTransform(FVector(0,0,140)));
        Modifier.Add(FMeshBoneInfo(HeadName,HeadName.ToString(),HeadParent), HeadPose);
    }
    // Populate the native BoneTree too; copied sequence models may consult retarget modes.
    USkeletalMesh* Source=NewObject<USkeletalMesh>(GetTransientPackage(),NAME_None,RF_Transient);
    Source->SetRefSkeleton(Result->GetReferenceSkeleton());
    Source->SetSkeleton(Result);
    ensureAlways(Result->MergeAllBonesToBoneTree(Source,false));
    return Result;
}

UAnimSequence* Sequence(const FString& Root, const TCHAR* Name, USkeleton* Reference, bool WithTrack=false)
{
    UAnimSequence* Result = NewObject<UAnimSequence>(FixturePackage(Root,Name), FName(Name), RF_Transient | RF_Transactional);
    Result->SetSkeleton(Reference);
    if (WithTrack)
    {
        IAnimationDataController& Controller = Result->GetController();
        Controller.InitializeModel();
        Controller.SetFrameRate(FFrameRate(30,1),false);
        Controller.SetNumberOfFrames(FFrameNumber(1),false);
        Controller.AddBoneCurve(TEXT("head"),false);
        Controller.SetBoneTrackKeys(TEXT("head"),
            TArray<FVector3f>{FVector3f(0,0,25),FVector3f(.25f,.5f,25.75f)},
            TArray<FQuat4f>{FQuat4f::Identity,FQuat4f::Identity},
            TArray<FVector3f>{FVector3f(1,1,1),FVector3f(1,1,1)},false);
        // No NotifyPopulated/compression/build is needed for this setter-isolation test.
    }
    return Result;
}

USkeletalMesh* Mesh(const FString& Root, const TCHAR* Name, USkeleton* Reference, bool WithInverse=true)
{
    USkeletalMesh* Result = NewObject<USkeletalMesh>(FixturePackage(Root,Name), FName(Name), RF_Transient | RF_Transactional);
    Result->SetSkeleton(Reference);
    Result->SetRefSkeleton(Reference->GetReferenceSkeleton());
    if (WithInverse)
    {
        TArray<FMatrix> Worlds;
        TArray<FMatrix44f> Inverses;
        const FReferenceSkeleton& Ref = Result->GetRefSkeleton();
        for (int32 Index=0;Index<Ref.GetNum();++Index)
        {
            const FMatrix Local = Ref.GetRefBonePose()[Index].ToMatrixWithScale();
            const int32 Parent = Ref.GetParentIndex(Index);
            const FMatrix World = Parent==INDEX_NONE ? Local : Local * Worlds[Parent];
            Worlds.Add(World);
            Inverses.Add(FMatrix44f(World.Inverse()));
        }
        Result->SetRefBasesInvMatrix(Inverses);
    }
    return Result;
}

bool UsableReadback(const FString& Json, bool NeedsInverse)
{
    if (Json.IsEmpty()) return false;
    TSharedPtr<FJsonObject> Object;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Object) || !Object.IsValid()) return false;
    const TArray<TSharedPtr<FJsonValue>>* Bones=nullptr;
    if (!Object->TryGetArrayField(TEXT("bones"),Bones) || !Bones || Bones->IsEmpty()) return false;
    if (NeedsInverse)
    {
        const TArray<TSharedPtr<FJsonValue>>* Inverses=nullptr;
        if (!Object->TryGetArrayField(TEXT("inverseBindProbes"),Inverses) || !Inverses || Inverses->Num()!=Bones->Num()) return false;
    }
    return true;
}

struct FSequenceState
{
    USkeleton* Reference;
    FGuid ReferenceGuid;
    FString ReferenceJson;
    bool SequencePackageDirty;
    bool ReferencePackageDirty;
    EObjectFlags SequenceFlags;
    const IAnimationDataModel* Model;
    FFrameRate FrameRate;
    int32 Frames;
    TArray<FName> Tracks;
    TMap<FName,TArray<FTransform>> Keys;

    explicit FSequenceState(UAnimSequence* Sequence)
        : Reference(Sequence->GetSkeleton()), ReferenceGuid(Reference->GetGuid()),
          ReferenceJson(UWarMageReviewLibrary::DescribeSkeletonReference(Reference)),
          SequencePackageDirty(Sequence->GetOutermost()->IsDirty()),
          ReferencePackageDirty(Reference->GetOutermost()->IsDirty()),
          SequenceFlags(Sequence->GetFlags()), Model(Sequence->GetDataModel()),
          FrameRate(Model->GetFrameRate()), Frames(Model->GetNumberOfFrames())
    {
        Model->GetBoneTrackNames(Tracks);
        for (const FName Track:Tracks) Model->GetBoneTrackTransforms(Track,Keys.Add(Track));
    }

    void VerifyUnchanged(FAutomationTestBase& Test,UAnimSequence* Sequence,const FString& Label) const
    {
        Test.TestTrue(Label+TEXT(" sequence keeps original skeleton pointer"),Sequence->GetSkeleton()==Reference);
        Test.TestTrue(Label+TEXT(" original skeleton GUID unchanged"),Reference->GetGuid()==ReferenceGuid);
        Test.TestEqual(Label+TEXT(" original reference readback unchanged"),
            UWarMageReviewLibrary::DescribeSkeletonReference(Reference),ReferenceJson);
        Test.TestEqual(Label+TEXT(" original sequence package dirty state unchanged"),Sequence->GetOutermost()->IsDirty(),SequencePackageDirty);
        Test.TestEqual(Label+TEXT(" original skeleton package dirty state unchanged"),Reference->GetOutermost()->IsDirty(),ReferencePackageDirty);
        Test.TestTrue(Label+TEXT(" original sequence flags unchanged"),Sequence->GetFlags()==SequenceFlags);
        const IAnimationDataModel* After=Sequence->GetDataModel();
        Test.TestTrue(Label+TEXT(" original data model object unchanged"),After==Model);
        Test.TestTrue(Label+TEXT(" original frame rate unchanged"),After->GetFrameRate()==FrameRate);
        Test.TestEqual(Label+TEXT(" original frame count unchanged"),After->GetNumberOfFrames(),Frames);
        TArray<FName> Names;After->GetBoneTrackNames(Names);
        Test.TestTrue(Label+TEXT(" original track names unchanged"),Names==Tracks);
        for (const FName Track:Tracks)
        {
            TArray<FTransform> Values;After->GetBoneTrackTransforms(Track,Values);
            const TArray<FTransform>& Before=Keys.FindChecked(Track);
            Test.TestEqual(Label+TEXT(" original track key count unchanged"),Values.Num(),Before.Num());
            if (Values.Num()!=Before.Num()) continue;
            for (int32 Key=0;Key<Values.Num();++Key)
                Test.TestTrue(Label+TEXT(" original keyed transform unchanged"),Values[Key].Equals(Before[Key],0.0));
        }
    }
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageReviewReadbackTest,
    "AegisWar.Foundation.MageReview.Readbacks",WarMageReviewTests::Flags)
bool FWarMageReviewReadbackTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReviewTests;
    TestTrue(TEXT("Null mesh readback is unavailable"),UWarMageReviewLibrary::DescribeSkeletalReference(nullptr).IsEmpty());
    TestTrue(TEXT("Null skeleton readback is unavailable"),UWarMageReviewLibrary::DescribeSkeletonReference(nullptr).IsEmpty());
    const FString Root=NewCandidateRoot();
    auto* EmptySkeleton=NewObject<USkeleton>(FixturePackage(Root,TEXT("EmptySkeleton")),TEXT("EmptySkeleton"),RF_Transient);
    auto* EmptyMesh=NewObject<USkeletalMesh>(FixturePackage(Root,TEXT("EmptyMesh")),TEXT("EmptyMesh"),RF_Transient);
    TestFalse(TEXT("Empty skeleton is not usable bind evidence"),UsableReadback(UWarMageReviewLibrary::DescribeSkeletonReference(EmptySkeleton),false));
    TestFalse(TEXT("Empty mesh is not usable bind evidence"),UsableReadback(UWarMageReviewLibrary::DescribeSkeletalReference(EmptyMesh),true));
    auto* InvalidSkeleton=Skeleton(Root,TEXT("InvalidSkeleton"));
    auto* InvalidMesh=Mesh(Root,TEXT("InvalidMesh"),InvalidSkeleton);
    InvalidMesh->MarkAsGarbage();InvalidSkeleton->MarkAsGarbage();
    TestTrue(TEXT("Garbage-marked mesh is rejected before reference access"),UWarMageReviewLibrary::DescribeSkeletalReference(InvalidMesh).IsEmpty());
    TestTrue(TEXT("Garbage-marked skeleton is rejected before reference access"),UWarMageReviewLibrary::DescribeSkeletonReference(InvalidSkeleton).IsEmpty());
    auto* Reference=Skeleton(Root,TEXT("Reference"));
    auto* MissingInverse=Mesh(Root,TEXT("MissingInverse"),Reference,false);
    TestFalse(TEXT("Mesh lacking stored inverse bind bases is not usable evidence"),UsableReadback(UWarMageReviewLibrary::DescribeSkeletalReference(MissingInverse),true));
    auto* Valid=Mesh(Root,TEXT("ValidMesh"),Reference);
    Valid->GetOutermost()->SetDirtyFlag(false);Reference->GetOutermost()->SetDirtyFlag(false);
    const FString First=UWarMageReviewLibrary::DescribeSkeletalReference(Valid);
    TestTrue(TEXT("Actual finite reference and inverse bases are usable"),UsableReadback(First,true));
    TestEqual(TEXT("Repeated native readback is stable"),UWarMageReviewLibrary::DescribeSkeletalReference(Valid),First);
    TestFalse(TEXT("Mesh readback leaves original package clean"),Valid->GetOutermost()->IsDirty());
    TestFalse(TEXT("Mesh readback leaves skeleton package clean"),Reference->GetOutermost()->IsDirty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageReviewNamespaceTest,
    "AegisWar.Foundation.MageReview.NamespaceIsolation",WarMageReviewTests::Flags)
bool FWarMageReviewNamespaceTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReviewTests;
    const FString Root=NewCandidateRoot();
    const FString OriginalRoot=TEXT("/Game/MageReviewAutomationOriginals/")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    auto* OriginalReference=Skeleton(OriginalRoot,TEXT("OriginalReference"));
    auto* Original=Sequence(OriginalRoot,TEXT("OriginalSequence"),OriginalReference,true);
    Original->GetOutermost()->SetDirtyFlag(false);OriginalReference->GetOutermost()->SetDirtyFlag(false);
    FSequenceState OriginalState(Original);
    auto* PrivateReference=Skeleton(Root,TEXT("PrivateReference"));
    auto* Private=Sequence(Root,TEXT("PrivateSequence"),OriginalReference,true);
    Private->GetOutermost()->SetDirtyFlag(false);PrivateReference->GetOutermost()->SetDirtyFlag(false);
    const FSequenceState PrivateState(Private);
    TestFalse(TEXT("Original sequence cannot be rebound even to private skeleton"),
        UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Original,PrivateReference,Root));
    TestFalse(TEXT("Original skeleton cannot be a rebind destination"),
        UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Private,OriginalReference,Root));
    TestFalse(TEXT("Null sequence is rejected"),UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(nullptr,PrivateReference,Root));
    TestFalse(TEXT("Null skeleton is rejected"),UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Private,nullptr,Root));
    auto* InvalidReference=Skeleton(Root,TEXT("GarbageReference"));
    auto* InvalidSequence=Sequence(Root,TEXT("GarbageSequence"),OriginalReference);
    InvalidSequence->MarkAsGarbage();InvalidReference->MarkAsGarbage();
    TestFalse(TEXT("Garbage-marked sequence rejected"),UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(InvalidSequence,PrivateReference,Root));
    TestFalse(TEXT("Garbage-marked destination rejected"),UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Private,InvalidReference,Root));
    const TArray<FString> InvalidRoots={TEXT("/Game/MageReviewAutomationOriginals"),Root+TEXT("/nested"),Root+TEXT(".asset"),Root+TEXT("\\nested"),
        TEXT("/Game/Characters/MageFaceDiagnostic/")};
    for (const FString& InvalidRoot:InvalidRoots)
        TestFalse(TEXT("Invalid supplied candidate root rejected"),UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Private,PrivateReference,InvalidRoot));
    const TArray<FString> InvalidSuffixRoots={TEXT("/Game/Characters/MageFaceDiagnostic/UPPER_")+FGuid::NewGuid().ToString(EGuidFormats::Digits),
        TEXT("/Game/Characters/MageFaceDiagnostic/")+FString::ChrN(97,TEXT('a'))};
    for (const FString& InvalidRoot:InvalidSuffixRoots)
    {
        // Objects physically occupy these otherwise valid package paths, isolating the suffix policy.
        auto* SuffixReference=Skeleton(InvalidRoot,TEXT("InvalidSuffixReference"));
        auto* SuffixSequence=Sequence(InvalidRoot,TEXT("InvalidSuffixSequence"),OriginalReference);
        TestFalse(TEXT("Uppercase or oversized suffix is rejected despite matching object paths"),
            UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(SuffixSequence,SuffixReference,InvalidRoot));
        TestTrue(TEXT("Invalid-suffix rejection preserves prior reference"),SuffixSequence->GetSkeleton()==OriginalReference);
    }
    const FString OtherRoot=NewCandidateRoot();
    auto* OtherReference=Skeleton(OtherRoot,TEXT("OtherReference"));
    TestFalse(TEXT("Another valid private candidate is not this candidate"),
        UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Private,OtherReference,Root));
    OriginalState.VerifyUnchanged(*this,Original,TEXT("Namespace rejections"));
    PrivateState.VerifyUnchanged(*this,Private,TEXT("Rejected private sequence"));
    TestFalse(TEXT("Rejected destination skeleton remains clean"),PrivateReference->GetOutermost()->IsDirty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageReviewReferenceMismatchTest,
    "AegisWar.Foundation.MageReview.ReferenceMismatch",WarMageReviewTests::Flags)
bool FWarMageReviewReferenceMismatchTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReviewTests;
    const FString Root=NewCandidateRoot();
    auto* Reference=Skeleton(Root,TEXT("SourceReference"));
    auto* Source=Sequence(Root,TEXT("PrivateSequence"),Reference,true);
    Source->GetOutermost()->SetDirtyFlag(false);Reference->GetOutermost()->SetDirtyFlag(false);
    const FSequenceState State(Source);
    TArray<USkeleton*> Rejected;
    Rejected.Add(Skeleton(Root,TEXT("ChangedName"),TEXT("changed_head")));
    Rejected.Add(Skeleton(Root,TEXT("ChangedParent"),TEXT("head"),0));
    Rejected.Add(Skeleton(Root,TEXT("ChangedTranslation"),TEXT("head"),1,FTransform(FVector(0,0,25.125))));
    Rejected.Add(Skeleton(Root,TEXT("ChangedRotation"),TEXT("head"),1,FTransform(FQuat(FVector::UpVector,.01),FVector(0,0,25))));
    Rejected.Add(Skeleton(Root,TEXT("ChangedScale"),TEXT("head"),1,FTransform(FQuat::Identity,FVector(0,0,25),FVector(1.01,1,1))));
    auto* CountMismatch=NewObject<USkeleton>(FixturePackage(Root,TEXT("ChangedCount")),TEXT("ChangedCount"),RF_Transient);
    {FReferenceSkeletonModifier Modifier(CountMismatch);Modifier.Add(FMeshBoneInfo(TEXT("root"),TEXT("root"),INDEX_NONE),FTransform::Identity);}
    Rejected.Add(CountMismatch);
    for (auto* Target:Rejected)
    {
        Target->GetOutermost()->SetDirtyFlag(false);
        const FString TargetBefore=UWarMageReviewLibrary::DescribeSkeletonReference(Target);
        TestFalse(TEXT("Mismatched names/parents/reference transforms cannot be rebound"),
            UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Source,Target,Root));
        State.VerifyUnchanged(*this,Source,Target->GetName());
        TestEqual(TEXT("Rejected target reference unchanged"),UWarMageReviewLibrary::DescribeSkeletonReference(Target),TargetBefore);
        TestFalse(TEXT("Rejected target package remains clean"),Target->GetOutermost()->IsDirty());
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageReviewCopiedReferenceTest,
    "AegisWar.Foundation.MageReview.IdenticalPrivateCopy",WarMageReviewTests::Flags)
bool FWarMageReviewCopiedReferenceTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReviewTests;
    for (const bool OriginallyDirty:{false,true})
    {
        const FString Root=NewCandidateRoot();
        const FString OriginalRoot=TEXT("/Game/MageReviewAutomationOriginals/")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        auto* OriginalReference=Skeleton(OriginalRoot,TEXT("OriginalReference"));
        auto* Original=Sequence(OriginalRoot,TEXT("OriginalSequence"),OriginalReference,true);
        auto* Target=DuplicateObject<USkeleton>(OriginalReference,FixturePackage(Root,TEXT("ReferenceCopy")),TEXT("ReferenceCopy"));
        auto* Copied=DuplicateObject<UAnimSequence>(Original,FixturePackage(Root,TEXT("SequenceCopy")),TEXT("SequenceCopy"));
        if (!TestNotNull(TEXT("Skeleton copy exists"),Target) || !TestNotNull(TEXT("Sequence copy exists"),Copied)) return false;
        Target->SetFlags(RF_Transient);Copied->SetFlags(RF_Transient);
        Original->GetOutermost()->SetDirtyFlag(OriginallyDirty);OriginalReference->GetOutermost()->SetDirtyFlag(OriginallyDirty);
        Target->GetOutermost()->SetDirtyFlag(false);Copied->GetOutermost()->SetDirtyFlag(false);
        const FSequenceState OriginalState(Original);
        const FString TargetReference=UWarMageReviewLibrary::DescribeSkeletonReference(Target);
        const FGuid TargetGuid=Target->GetGuid();
        TArray<FTransform> OriginalKeys,CopiedKeys;
        Original->GetDataModel()->GetBoneTrackTransforms(TEXT("head"),OriginalKeys);
        TestEqual(TEXT("Source fixture has two real controller-authored keys"),OriginalKeys.Num(),2);
        TestTrue(TEXT("Identical copied private references are accepted"),
            UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Copied,Target,Root));
        TestTrue(TEXT("Only duplicated sequence now points at copied skeleton"),Copied->GetSkeleton()==Target);
        Copied->GetDataModel()->GetBoneTrackTransforms(TEXT("head"),CopiedKeys);
        TestEqual(TEXT("Accepted copy preserves source key count"),CopiedKeys.Num(),OriginalKeys.Num());
        if (CopiedKeys.Num()==OriginalKeys.Num())
            for(int32 Index=0;Index<CopiedKeys.Num();++Index)
                TestTrue(TEXT("Accepted copy preserves exact keyed transforms"),CopiedKeys[Index].Equals(OriginalKeys[Index],0.0));
        TestEqual(TEXT("Copied reference remains exact"),UWarMageReviewLibrary::DescribeSkeletonReference(Target),TargetReference);
        TestTrue(TEXT("Copied reference GUID remains exact"),Target->GetGuid()==TargetGuid);
        TestFalse(TEXT("Copied reference package is not dirtied by sequence assignment"),Target->GetOutermost()->IsDirty());
        OriginalState.VerifyUnchanged(*this,Original,OriginallyDirty?TEXT("Previously dirty originals"):TEXT("Clean originals"));
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageReviewEmptyReferenceTest,
    "AegisWar.Foundation.MageReview.EmptyReferenceRejected",WarMageReviewTests::Flags)
bool FWarMageReviewEmptyReferenceTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReviewTests;
    const FString Root=NewCandidateRoot();
    auto* First=NewObject<USkeleton>(FixturePackage(Root,TEXT("FirstEmpty")),TEXT("FirstEmpty"),RF_Transient);
    auto* Second=NewObject<USkeleton>(FixturePackage(Root,TEXT("SecondEmpty")),TEXT("SecondEmpty"),RF_Transient);
    auto* EmptySequence=Sequence(Root,TEXT("EmptySequence"),First);
    EmptySequence->GetOutermost()->SetDirtyFlag(false);First->GetOutermost()->SetDirtyFlag(false);Second->GetOutermost()->SetDirtyFlag(false);
    TestFalse(TEXT("Two equally empty references are not an acceptable rig"),
        UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(EmptySequence,Second,Root));
    TestTrue(TEXT("Empty-reference rejection preserves prior skeleton"),EmptySequence->GetSkeleton()==First);
    TestFalse(TEXT("Empty-reference rejection leaves original sequence clean"),EmptySequence->GetOutermost()->IsDirty());
    TestFalse(TEXT("Empty-reference rejection leaves original reference clean"),First->GetOutermost()->IsDirty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageReviewThreadAndSizeTest,
    "AegisWar.Foundation.MageReview.ThreadAndSizeGuards",WarMageReviewTests::Flags)
bool FWarMageReviewThreadAndSizeTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReviewTests;
    const FString Root=NewCandidateRoot();
    auto* Reference=Skeleton(Root,TEXT("Reference"));
    auto* Target=Skeleton(Root,TEXT("Target"));
    auto* Private=Sequence(Root,TEXT("PrivateSequence"),Reference,true);
    auto* ValidMesh=Mesh(Root,TEXT("ValidMesh"),Reference);
    Private->GetOutermost()->SetDirtyFlag(false);Reference->GetOutermost()->SetDirtyFlag(false);
    const FSequenceState State(Private);
    struct FOffThreadResult{FString SkeletonJson;FString MeshJson;bool Assigned;};
    // Bridge thread guards short-circuit before dereferencing UObjects; no worker-side fixture mutation.
    auto Worker=Async(EAsyncExecution::ThreadPool,[Reference,Target,Private,ValidMesh,Root]()
    {
        return FOffThreadResult{UWarMageReviewLibrary::DescribeSkeletonReference(Reference),
            UWarMageReviewLibrary::DescribeSkeletalReference(ValidMesh),
            UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Private,Target,Root)};
    });
    const FOffThreadResult OffThread=Worker.Get();
    TestTrue(TEXT("Off-game-thread skeleton readback rejected before access"),OffThread.SkeletonJson.IsEmpty());
    TestTrue(TEXT("Off-game-thread mesh readback rejected before access"),OffThread.MeshJson.IsEmpty());
    TestFalse(TEXT("Off-game-thread private sequence assignment rejected"),OffThread.Assigned);
    State.VerifyUnchanged(*this,Private,TEXT("Off-thread rejection"));
    auto* Oversized=NewObject<USkeleton>(FixturePackage(Root,TEXT("Oversized")),TEXT("Oversized"),RF_Transient);
    {
        FReferenceSkeletonModifier Modifier(Oversized);
        Modifier.Add(FMeshBoneInfo(TEXT("root"),TEXT("root"),INDEX_NONE),FTransform::Identity);
        for(int32 Index=1;Index<=4096;++Index)
        {
            const FString Name=FString::Printf(TEXT("bone_%d"),Index);
            Modifier.Add(FMeshBoneInfo(FName(*Name),Name,0),FTransform::Identity);
        }
    }
    TestEqual(TEXT("Oversized fixture crosses the native upper bound"),Oversized->GetReferenceSkeleton().GetNum(),4097);
    TestTrue(TEXT("Over-4096 skeleton readback rejected"),UWarMageReviewLibrary::DescribeSkeletonReference(Oversized).IsEmpty());
    auto* OversizedMesh=Mesh(Root,TEXT("OversizedMesh"),Oversized);
    TestTrue(TEXT("Over-4096 mesh readback rejected"),UWarMageReviewLibrary::DescribeSkeletalReference(OversizedMesh).IsEmpty());
    auto* OversizedCopy=DuplicateObject<USkeleton>(Oversized,FixturePackage(Root,TEXT("OversizedCopy")),TEXT("OversizedCopy"));
    auto* OversizedSequence=Sequence(Root,TEXT("OversizedSequence"),Oversized);
    TestFalse(TEXT("Two equally oversized references cannot be assigned"),
        UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(OversizedSequence,OversizedCopy,Root));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageReviewFiniteReferenceTest,
    "AegisWar.Foundation.MageReview.FiniteReferenceGuard",WarMageReviewTests::Flags)
bool FWarMageReviewFiniteReferenceTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReviewTests;
#if !ENABLE_NAN_DIAGNOSTIC
    // Builds enabling transform diagnostics intentionally assert during malformed fixture construction.
    // The ordinary Development Editor build can reach the bridge guard without bypassing engine accessors.
    const FString Root=NewCandidateRoot();
    auto* Reference=Skeleton(Root,TEXT("FiniteSource"));
    auto* Target=Skeleton(Root,TEXT("NonfiniteTarget"));
    auto* Private=Sequence(Root,TEXT("PrivateSequence"),Reference,true);
    Private->GetOutermost()->SetDirtyFlag(false);Reference->GetOutermost()->SetDirtyFlag(false);
    const FSequenceState Before(Private);
    FTransform Bad=FTransform(FVector(0,0,25));
    Bad.SetScale3D(FVector(std::numeric_limits<double>::infinity(),1,1));
    {FReferenceSkeletonModifier Modifier(Target);Modifier.UpdateRefPoseTransform(2,Bad);}
    TestTrue(TEXT("Fixture actually stores a nonfinite reference transform"),Target->GetReferenceSkeleton().GetRefBonePose()[2].ContainsNaN());
    TestFalse(TEXT("Nonfinite target reference rejected before setter"),
        UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(Private,Target,Root));
    Before.VerifyUnchanged(*this,Private,TEXT("Nonfinite target rejection"));
    auto* NonfiniteSource=Sequence(Root,TEXT("NonfiniteSourceSequence"),Target);
    TestFalse(TEXT("Nonfinite previous reference rejected before setter"),
        UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(NonfiniteSource,Reference,Root));
    TestTrue(TEXT("Rejected nonfinite source sequence preserves its prior pointer"),NonfiniteSource->GetSkeleton()==Target);
#else
    AddInfo(TEXT("Malformed-transform fixture skipped because ENABLE_NAN_DIAGNOSTIC asserts before bridge access; other native guards still execute."));
#endif
    return true;
}
#endif
