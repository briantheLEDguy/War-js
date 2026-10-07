#include "WarMageReviewLibrary.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
bool ValidReference(const FReferenceSkeleton& Reference)
{
    const int32 Count = Reference.GetNum();
    if (Count < 1 || Count > 4096 || Reference.GetRefBonePose().Num() != Count) return false;
    for (int32 I = 0; I < Count; ++I)
    {
        const int32 Parent = Reference.GetParentIndex(I);
        if (Parent < INDEX_NONE || Parent >= I || Reference.GetRefBonePose()[I].ContainsNaN()) return false;
    }
    return true;
}

template<typename MatrixType>
TArray<TSharedPtr<FJsonValue>> ProbeMatrix(const MatrixType& Matrix)
{
    TArray<TSharedPtr<FJsonValue>> Result;
    for (const FVector Point : {FVector::ZeroVector, FVector(100,0,0), FVector(0,100,0), FVector(0,0,100)})
    {
        const FVector Value(
            Point.X * Matrix.M[0][0] + Point.Y * Matrix.M[1][0] + Point.Z * Matrix.M[2][0] + Matrix.M[3][0],
            Point.X * Matrix.M[0][1] + Point.Y * Matrix.M[1][1] + Point.Z * Matrix.M[2][1] + Matrix.M[3][1],
            Point.X * Matrix.M[0][2] + Point.Y * Matrix.M[1][2] + Point.Z * Matrix.M[2][2] + Matrix.M[3][2]);
        Result.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
            MakeShared<FJsonValueNumber>(Value.X), MakeShared<FJsonValueNumber>(Value.Y),
            MakeShared<FJsonValueNumber>(Value.Z)}));
    }
    return Result;
}

TSharedRef<FJsonObject> DescribeReference(const FReferenceSkeleton& Reference)
{
    auto Result = MakeShared<FJsonObject>();
    TArray<FMatrix> Worlds;
    TArray<TSharedPtr<FJsonValue>> Bones;
    const auto& Transforms = Reference.GetRefBonePose();
    for (int32 Index = 0; Index < Reference.GetNum(); ++Index)
    {
        const int32 Parent = Reference.GetParentIndex(Index);
        const FMatrix Local = Transforms[Index].ToMatrixWithScale();
        const FMatrix World = Parent == INDEX_NONE ? Local : Local * Worlds[Parent];
        Worlds.Add(World);
        auto Bone = MakeShared<FJsonObject>();
        Bone->SetStringField(TEXT("name"), Reference.GetBoneName(Index).ToString());
        Bone->SetNumberField(TEXT("parent"), Parent);
        Bone->SetArrayField(TEXT("localProbesCm"), ProbeMatrix(Local));
        Bone->SetArrayField(TEXT("worldProbesCm"), ProbeMatrix(World));
        Bones.Add(MakeShared<FJsonValueObject>(Bone));
    }
    Result->SetNumberField(TEXT("schemaVersion"), 1);
    Result->SetArrayField(TEXT("bones"), Bones);
    return Result;
}

FString Json(const TSharedRef<FJsonObject>& Value)
{
    FString Result;
    FJsonSerializer::Serialize(Value, TJsonWriterFactory<>::Create(&Result));
    return Result;
}

bool IsCandidateObject(const UObject* Object, const FString& Root)
{
    const FString Prefix(TEXT("/Game/Characters/MageFaceDiagnostic/"));
    const FString Suffix = Root.RightChop(Prefix.Len());
    if (!IsValid(Object) || !Root.StartsWith(Prefix) || Suffix.IsEmpty() || Suffix.Len() > 96) return false;
    for (const TCHAR C : Suffix)
        if (!((C >= TEXT('a') && C <= TEXT('z')) || (C >= TEXT('0') && C <= TEXT('9')) || C == TEXT('_'))) return false;
    return Object->GetOutermost()->GetName().StartsWith(Root + TEXT("/"));
}
}

FString UWarMageReviewLibrary::DescribeSkeletalReference(const USkeletalMesh* Mesh)
{
    if (!IsInGameThread() || !IsValid(Mesh) || !ValidReference(Mesh->GetRefSkeleton())
        || Mesh->GetRefBasesInvMatrix().Num() != Mesh->GetRefSkeleton().GetNum()) return FString();
    for (const auto& Matrix : Mesh->GetRefBasesInvMatrix()) if (Matrix.ContainsNaN()) return FString();
    auto Result = DescribeReference(Mesh->GetRefSkeleton());
    TArray<TSharedPtr<FJsonValue>> Inverses;
    for (const FMatrix44f& Matrix : Mesh->GetRefBasesInvMatrix())
        Inverses.Add(MakeShared<FJsonValueArray>(ProbeMatrix(Matrix)));
    Result->SetArrayField(TEXT("inverseBindProbes"), Inverses);
    Result->SetStringField(TEXT("asset"), Mesh->GetPathName());
    return Json(Result);
}

FString UWarMageReviewLibrary::DescribeSkeletonReference(const USkeleton* Skeleton)
{
    if (!IsInGameThread() || !IsValid(Skeleton) || !ValidReference(Skeleton->GetReferenceSkeleton())) return FString();
    return Json(DescribeReference(Skeleton->GetReferenceSkeleton()));
}

bool UWarMageReviewLibrary::AssignDiagnosticSequenceSkeleton(UAnimSequence* Sequence,
    USkeleton* Skeleton, const FString& CandidateRoot)
{
    if (!IsInGameThread() || !IsCandidateObject(Sequence, CandidateRoot) || !IsCandidateObject(Skeleton, CandidateRoot) ||
        !Sequence->GetSkeleton()) return false;
    const FReferenceSkeleton& Previous = Sequence->GetSkeleton()->GetReferenceSkeleton();
    const FReferenceSkeleton& Next = Skeleton->GetReferenceSkeleton();
    if (!ValidReference(Previous) || !ValidReference(Next) || Previous.GetNum() != Next.GetNum()) return false;
    for (int32 Index = 0; Index < Previous.GetNum(); ++Index)
    {
        if (Previous.GetRefBonePose()[Index].ContainsNaN() || Next.GetRefBonePose()[Index].ContainsNaN() ||
            Previous.GetBoneName(Index) != Next.GetBoneName(Index) ||
            Previous.GetParentIndex(Index) != Next.GetParentIndex(Index) ||
            !Previous.GetRefBonePose()[Index].Equals(Next.GetRefBonePose()[Index], 1.e-6)) return false;
    }
    // Uses the supported native setter. No retarget, track rewrite, old-skeleton edit or package save.
    Sequence->Modify();
    Sequence->SetSkeleton(Skeleton);
    Sequence->ValidateSkeleton();
    return Sequence->GetSkeleton() == Skeleton;
}
