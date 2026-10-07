#include "WarImportLibrary.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Factories/FbxAnimSequenceImportData.h"
#include "Modules/ModuleManager.h"
#include "Engine/StaticMesh.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "PhysicsEngine/BodySetup.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "Misc/PackageName.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BoxComponent.h"
#include "GameFramework/Actor.h"
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#include "RenderingThread.h"
#include "Engine/World.h"
#include "Engine/LevelStreaming.h"
#include "Engine/Level.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "StaticMeshResources.h"
#include "DistanceFieldAtlas.h"
#include "MeshCardBuild.h"
#include "RayTracingGeometry.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarCitadelSiegeProof.h"
#include "JsonObjectConverter.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Materials/MaterialExpression.h"
#include "Materials/Material.h"
#include "UObject/NoExportTypes.h"
#include <type_traits>

IMPLEMENT_MODULE(FDefaultModuleImpl, AegisWarEditorTools);

FString UWarImportLibrary::DescribeMaterialExpressionPins(UMaterialExpression* Expression)
{
    auto Report=MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"),1);
    Report->SetBoolField(TEXT("readOnly"),true);
    Report->SetBoolField(TEXT("available"),false);
    if (IsInGameThread() && IsValid(Expression))
    {
        const int32 InputCount=Expression->CountInputs();
        const auto& Outputs=Expression->GetOutputs();
        if (InputCount>=0 && InputCount<=256 && Outputs.Num()<=1024)
        {
            TArray<TSharedPtr<FJsonValue>> InputsJson,OutputsJson;
            bool bValid=true;
            for (int32 Index=0;Index<InputCount;++Index)
            {
                const FExpressionInput* Input=Expression->GetInput(Index);
                if (!Input || (Input->Expression && !IsValid(Input->Expression))) { bValid=false;break; }
                auto Row=MakeShared<FJsonObject>();
                Row->SetNumberField(TEXT("inputIndex"),Index);
                const FName InputName=Expression->GetInputName(Index);
                Row->SetStringField(TEXT("input_name"),InputName.IsNone()?FString():InputName.ToString());
                if (Input->Expression) Row->SetStringField(TEXT("node"),Input->Expression->GetName());
                else Row->SetField(TEXT("node"),MakeShared<FJsonValueNull>());
                Row->SetNumberField(TEXT("output_index"),Input->OutputIndex);
                Row->SetNumberField(TEXT("mask"),Input->Mask);
                Row->SetNumberField(TEXT("mask_r"),Input->MaskR);
                Row->SetNumberField(TEXT("mask_g"),Input->MaskG);
                Row->SetNumberField(TEXT("mask_b"),Input->MaskB);
                Row->SetNumberField(TEXT("mask_a"),Input->MaskA);
                InputsJson.Add(MakeShared<FJsonValueObject>(Row));
            }
            for (const FExpressionOutput& Output:Outputs)
            {
                auto Row=MakeShared<FJsonObject>();
                Row->SetStringField(TEXT("output_name"),Output.OutputName.IsNone()?FString():Output.OutputName.ToString());
                Row->SetNumberField(TEXT("mask"),Output.Mask);
                Row->SetNumberField(TEXT("mask_r"),Output.MaskR);
                Row->SetNumberField(TEXT("mask_g"),Output.MaskG);
                Row->SetNumberField(TEXT("mask_b"),Output.MaskB);
                Row->SetNumberField(TEXT("mask_a"),Output.MaskA);
                OutputsJson.Add(MakeShared<FJsonValueObject>(Row));
            }
            if (bValid)
            {
                Report->SetBoolField(TEXT("available"),true);
                Report->SetStringField(TEXT("expression"),Expression->GetPathName());
                Report->SetArrayField(TEXT("inputs"),InputsJson);
                Report->SetArrayField(TEXT("outputs"),OutputsJson);
            }
        }
    }
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));return Json;
}

namespace
{
    TSharedRef<FJsonObject> MaterialInputJson(const FExpressionInput& Input)
    {
        auto Row=MakeShared<FJsonObject>();
        if (Input.Expression) Row->SetStringField(TEXT("node"),Input.Expression->GetName());
        else Row->SetField(TEXT("node"),MakeShared<FJsonValueNull>());
        Row->SetNumberField(TEXT("output_index"),Input.OutputIndex);
        Row->SetNumberField(TEXT("mask"),Input.Mask);
        Row->SetNumberField(TEXT("mask_r"),Input.MaskR);
        Row->SetNumberField(TEXT("mask_g"),Input.MaskG);
        Row->SetNumberField(TEXT("mask_b"),Input.MaskB);
        Row->SetNumberField(TEXT("mask_a"),Input.MaskA);
        return Row;
    }
    struct FCitadelTerrainArrays
    {
        TArray<FVector3f> Positions, Normals, Tangents;
        TArray<FVector4f> Colors;
        TArray<float> Signs;
        TArray<TArray<FVector2f>> UVs;
        TArray<int32> Indices, Materials;
    };
    bool JsonEqual(const TSharedPtr<FJsonValue>& A, const TSharedPtr<FJsonValue>& B)
    { return A && B && FJsonValue::CompareEqual(*A, *B); }
    bool JsonInteger(const TSharedPtr<FJsonValue>& Value, int32& Out)
    {
        double Number = 0;
        if (!Value || Value->Type != EJson::Number || !Value->TryGetNumber(Number) || !FMath::IsFinite(Number)
            || Number < MIN_int32 || Number > MAX_int32 || Number != FMath::FloorToDouble(Number)) return false;
        Out = int32(Number); return true;
    }
    bool JsonVector(const TSharedPtr<FJsonValue>& Value, int32 Size, double* Out)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Value || !Value->TryGetArray(Values) || Values->Num() != Size) return false;
        for (int32 Index = 0; Index < Size; ++Index)
            if ((*Values)[Index]->Type != EJson::Number || !(*Values)[Index]->TryGetNumber(Out[Index])
                || !FMath::IsFinite(Out[Index]) || FMath::Abs(Out[Index]) > MAX_flt) return false;
        return true;
    }
    bool TerrainArrays(const TSharedPtr<FJsonObject>& Data, int32 MaterialCount, FCitadelTerrainArrays& Out)
    {
        const TArray<TSharedPtr<FJsonValue>> *Positions = nullptr, *Indices = nullptr, *Materials = nullptr, *Channels = nullptr;
        if (!Data || !Data->TryGetArrayField(TEXT("positions"), Positions) || Positions->IsEmpty() || Positions->Num() > 2000000
            || !Data->TryGetArrayField(TEXT("indices"), Indices) || Indices->IsEmpty() || Indices->Num() % 3 || Indices->Num() > 6000000
            || !Data->TryGetArrayField(TEXT("triangleMaterials"), Materials) || Materials->Num() * 3 != Indices->Num()
            || !Data->TryGetArrayField(TEXT("uvChannels"), Channels) || Channels->IsEmpty() || Channels->Num() > 8) return false;
        const auto ReadVectors = [Positions](const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, int32 Dimension, auto& Output)
        {
            const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
            if (!Object->TryGetArrayField(Key, Values) || Values->Num() != Positions->Num()) return false;
            for (const auto& Value : *Values)
            {
                double V[4] = {}; if (!JsonVector(Value,Dimension,V)) return false;
                using Element = typename std::decay_t<decltype(Output)>::ElementType;
                if constexpr (std::is_same_v<Element,FVector4f>) Output.Add(FVector4f(float(V[0]),float(V[1]),float(V[2]),float(V[3])));
                else Output.Add(FVector3f(float(V[0]),float(V[1]),float(V[2])));
            }
            return true;
        };
        if (!ReadVectors(Data,TEXT("positions"),3,Out.Positions) || !ReadVectors(Data,TEXT("normals"),3,Out.Normals)) return false;
        if (Data->HasField(TEXT("tangents")) && !ReadVectors(Data,TEXT("tangents"),3,Out.Tangents)) return false;
        if (Data->HasField(TEXT("vertexColors")) && !ReadVectors(Data,TEXT("vertexColors"),4,Out.Colors)) return false;
        const TArray<TSharedPtr<FJsonValue>>* Signs = nullptr;
        if (Data->HasField(TEXT("binormalSigns")))
        {
            if (!Data->TryGetArrayField(TEXT("binormalSigns"),Signs) || Signs->Num()!=Positions->Num()) return false;
            for (const auto& Value:*Signs)
            {
                double Sign=0; if (Value->Type!=EJson::Number || !Value->TryGetNumber(Sign) || !FMath::IsFinite(Sign) || FMath::Abs(Sign)>MAX_flt) return false;
                Out.Signs.Add(float(Sign));
            }
        }
        for (const auto& Value:*Indices)
        { int32 Index; if (!JsonInteger(Value,Index) || Index<0 || Index>=Positions->Num()) return false; Out.Indices.Add(Index); }
        for (const auto& Value:*Materials)
        { int32 Index; if (!JsonInteger(Value,Index) || Index<0 || Index>=MaterialCount) return false; Out.Materials.Add(Index); }
        for (const auto& Channel:*Channels)
        {
            const TArray<TSharedPtr<FJsonValue>>* UVs=nullptr;
            if (!Channel->TryGetArray(UVs) || UVs->Num()!=Positions->Num()) return false;
            TArray<FVector2f>& Dest=Out.UVs.AddDefaulted_GetRef();
            for (const auto& UV:*UVs) { double V[2]; if (!JsonVector(UV,2,V)) return false; Dest.Add(FVector2f(float(V[0]),float(V[1]))); }
        }
        return JsonEqual(Data->TryGetField(TEXT("uvs")),(*Channels)[0]);
    }

    struct FCitadelCarveTriangle { FVector Weights[3]; };
    bool ExpectedCarve(const FVector* Source, const FVector& Min, const FVector& Max,
        TArray<FCitadelCarveTriangle>& Triangles, bool& bTouched)
    {
        // Independently reproduce the signed convex subtraction, including its fan order.
        // Area alone would allow a missing exterior fragment to be replaced by a duplicate.
        constexpr double Epsilon=1e-7,AreaEpsilon=1e-9;
        const auto Point=[Source](const FVector& Weight)
        {return Source[0]*Weight.X+Source[1]*Weight.Y+Source[2]*Weight.Z;};
        const auto Area=[&Point](const TArray<FVector>& Polygon)
        {
            double Total=0;
            for (int32 I=1;I+1<Polygon.Num();++I)
                Total+=FVector::CrossProduct(Point(Polygon[I])-Point(Polygon[0]),Point(Polygon[I+1])-Point(Polygon[0])).Size()*.5;
            return Total;
        };
        const auto Clean=[&Point,&Area](TArray<FVector> Polygon)
        {
            TArray<FVector> Result;
            for (const FVector& Weight:Polygon)
                if (Result.IsEmpty() || FVector::Distance(Point(Weight),Point(Result.Last()))>Epsilon) Result.Add(Weight);
            if (Result.Num()>1 && FVector::Distance(Point(Result[0]),Point(Result.Last()))<=Epsilon) Result.Pop();
            if (Result.Num()<3 || Area(Result)<=AreaEpsilon) Result.Reset();
            return Result;
        };
        const TArray<FVector> Identity={FVector(1,0,0),FVector(0,1,0),FVector(0,0,1)};
        if (Area(Identity)<=AreaEpsilon) return false;
        TArray<FVector> Remainder=Identity;TArray<TArray<FVector>> Exterior;
        for (int32 Axis=0;Axis<3;++Axis)
            for (int32 Side=0;Side<2;++Side)
            {
                if (Remainder.IsEmpty()) break;
                const double Boundary=Side==0?Min[Axis]:Max[Axis],Direction=Side==0?-1.:1.;
                TArray<double> Values;bool Coplanar=true;
                for (const FVector& Weight:Remainder)
                {const double Value=Direction*(Point(Weight)[Axis]-Boundary);Values.Add(Value);Coplanar&=FMath::Abs(Value)<=Epsilon;}
                if (Coplanar) continue;
                TArray<FVector> Inside,Outside;
                for (int32 I=0;I<Remainder.Num();++I)
                {
                    const int32 Next=(I+1)%Remainder.Num();const FVector A=Remainder[I],B=Remainder[Next];
                    const double Da=Values[I],Db=Values[Next];
                    if (Da<=Epsilon) Inside.Add(A);
                    if (Da>=-Epsilon) Outside.Add(A);
                    if ((Da<-Epsilon && Db>Epsilon) || (Da>Epsilon && Db<-Epsilon))
                    {const FVector Weight=A+(B-A)*(Da/(Da-Db));Inside.Add(Weight);Outside.Add(Weight);}
                }
                Remainder=Clean(MoveTemp(Inside));Outside=Clean(MoveTemp(Outside));
                if (!Outside.IsEmpty()) Exterior.Add(MoveTemp(Outside));
            }
        bTouched=Area(Remainder)>AreaEpsilon;
        if (!bTouched) {Triangles.Add({{Identity[0],Identity[1],Identity[2]}});return true;}
        const FVector OriginalNormal=FVector::CrossProduct(Source[1]-Source[0],Source[2]-Source[0]);
        for (const auto& Polygon:Exterior)
            for (int32 I=1;I+1<Polygon.Num();++I)
            {
                const FVector Normal=FVector::CrossProduct(Point(Polygon[I])-Point(Polygon[0]),Point(Polygon[I+1])-Point(Polygon[0]));
                if (Normal.Size()*.5<=AreaEpsilon) continue;
                if (FVector::DotProduct(Normal,OriginalNormal)<=0 || Triangles.Num()>=64) return false;
                Triangles.Add({{Polygon[0],Polygon[I],Polygon[I+1]}});
            }
        return true;
    }

    UStaticMesh* ImportCarvedTerrain(UStaticMesh* Source, const FString& Collection, const FString& Json, bool bFixture)
    {
        const auto Reject=[](const TCHAR* Reason)->UStaticMesh*
        { UE_LOG(LogTemp,Warning,TEXT("Citadel terrain clone rejected: %s"),Reason);return nullptr; };
        if (!IsInGameThread() || !IsValid(Source)) return Reject(TEXT("missing source mesh"));
        if (!bFixture && Source->GetPathName()!=TEXT("/Game/Capitals/crownward/Terrain_mountain.Terrain_mountain"))
            return Reject(TEXT("source is not the exact retained mountain"));
        const FString Prefix=TEXT("AegisCitadel_");
        if (!Collection.StartsWith(Prefix) || Collection.Len()!=Prefix.Len()+12) return Reject(TEXT("unowned collection"));
        for (TCHAR Character:Collection.Mid(Prefix.Len()))
            if (!FChar::IsDigit(Character) && (Character<TEXT('a') || Character>TEXT('f'))) return Reject(TEXT("noncanonical collection"));
        const FString Name=TEXT("SM_HallCarvedMountain"),PackageName=TEXT("/Game/WorldRebuild/")+Collection+TEXT("/Meshes/")+Name;
        if (FindPackage(nullptr,*PackageName) || FPackageName::DoesPackageExist(PackageName)) return Reject(TEXT("target already exists"));
        if (Json.Len()==0 || Json.Len()>128*1024*1024) return Reject(TEXT("missing or unbounded clip document"));
        TSharedPtr<FJsonObject> Document;
        if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Document)) return Reject(TEXT("malformed clip JSON"));
        const TSet<FString> Keys={TEXT("schemaVersion"),TEXT("sourceMesh"),TEXT("sourceExportPayload"),TEXT("sourceExportSha256"),
            TEXT("actorTransform"),TEXT("worldVolumes"),TEXT("localVolumeBounds"),TEXT("data"),TEXT("carveReceipt")};
        if (Document->Values.Num()!=Keys.Num()) return Reject(TEXT("unknown clip schema members"));
        for (const auto& Pair:Document->Values) if (!Keys.Contains(FString(*Pair.Key))) return Reject(TEXT("unknown clip schema member"));
        double Version=0;FString SourcePath,Payload,ExpectedHash,ActualHash,HashError;
        if (!Document->TryGetNumberField(TEXT("schemaVersion"),Version) || Version!=1
            || !Document->TryGetStringField(TEXT("sourceMesh"),SourcePath) || SourcePath!=Source->GetPathName()
            || !Document->TryGetStringField(TEXT("sourceExportPayload"),Payload)
            || !Document->TryGetStringField(TEXT("sourceExportSha256"),ExpectedHash)
            || !WarCitadelProofHash::Text(Payload,ActualHash,HashError) || ActualHash!=ExpectedHash)
            return Reject(TEXT("source identity or raw source SHA changed"));
        TSharedPtr<FJsonObject> Export,Current;
        if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Payload),Export)
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeStaticMeshSourceData(Source)),Current)
            || !FJsonValue::CompareEqual(FJsonValueObject(Export),FJsonValueObject(Current))
            || !Current->GetBoolField(TEXT("valid"))) return Reject(TEXT("source differs from actual committed corner data"));
        const TSharedPtr<FJsonObject> *DataPtr=nullptr,*ReceiptPtr=nullptr,*TransformPtr=nullptr;
        if (!Document->TryGetObjectField(TEXT("data"),DataPtr) || !Document->TryGetObjectField(TEXT("carveReceipt"),ReceiptPtr)
            || !Document->TryGetObjectField(TEXT("actorTransform"),TransformPtr)) return Reject(TEXT("missing clip provenance"));
        const auto Data=*DataPtr,Receipt=*ReceiptPtr,Original=Current->GetObjectField(TEXT("data"));
        FCitadelTerrainArrays SourceArrays,Arrays;
        if (!TerrainArrays(Original,Source->GetStaticMaterials().Num(),SourceArrays) || !TerrainArrays(Data,Source->GetStaticMaterials().Num(),Arrays)
            || Original->Values.Num()!=Data->Values.Num()) return Reject(TEXT("missing or invalid corner attributes"));
        for (const auto& Pair:Original->Values)
        {
            const FString Key(*Pair.Key);
            if (!Data->HasField(Key)) return Reject(TEXT("source attributes were dropped"));
            if (Key==TEXT("indices") || Key==TEXT("triangleMaterials")) continue;
            const auto& Old=Pair.Value->AsArray();const auto& Added=Data->GetArrayField(Key);
            if (Key==TEXT("uvChannels"))
            {
                if (Old.Num()!=Added.Num()) return Reject(TEXT("UV channels changed"));
                for (int32 C=0;C<Old.Num();++C)
                {
                    const auto& A=Old[C]->AsArray();const auto& B=Added[C]->AsArray();
                    if (B.Num()<A.Num()) return Reject(TEXT("UV prefix removed"));
                    for (int32 I=0;I<A.Num();++I) if (!JsonEqual(A[I],B[I])) return Reject(TEXT("committed UV prefix changed"));
                }
            }
            else
            {
                if (Added.Num()<Old.Num()) return Reject(TEXT("original corner prefix removed"));
                for (int32 I=0;I<Old.Num();++I) if (!JsonEqual(Old[I],Added[I])) return Reject(TEXT("committed attribute prefix changed"));
            }
        }
        const FString Frame=TEXT("{\"translationCm\":[25000,0,0],\"rotationQuaternion\":[0,0,0,1],\"scale\":[1,1,1]}");
        const FString Volumes=TEXT("[{\"id\":\"occupied_commander_hall\",\"coordinateSpace\":\"world_cm\",\"bounds\":[[25960,-4260,5980],[33460,4260,24000]]}]");
        const FString Local=TEXT("[[[960,-4260,5980],[8460,4260,24000]]]");
        TSharedPtr<FJsonValue> ExpectedFrame,ExpectedVolumes,ExpectedLocal;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Frame),ExpectedFrame);
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Volumes),ExpectedVolumes);
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Local),ExpectedLocal);
        if (!JsonEqual(Document->TryGetField(TEXT("actorTransform")),ExpectedFrame)
            || !JsonEqual(Document->TryGetField(TEXT("worldVolumes")),ExpectedVolumes)
            || !JsonEqual(Document->TryGetField(TEXT("localVolumeBounds")),ExpectedLocal)
            || !JsonEqual(Receipt->TryGetField(TEXT("actorTransform")),ExpectedFrame)
            || !JsonEqual(Receipt->TryGetField(TEXT("worldVolumes")),ExpectedVolumes)
            || !JsonEqual(Receipt->TryGetField(TEXT("localVolumeBounds")),ExpectedLocal)) return Reject(TEXT("carve escaped the measured hall frame"));
        FString Method,Winding;bool GeometryOnly=false;double ReceiptVersion=0,SourceTriangles=0,OutputTriangles=0;
        if (!Receipt->TryGetNumberField(TEXT("schemaVersion"),ReceiptVersion) || ReceiptVersion!=1
            || !Receipt->TryGetBoolField(TEXT("geometryOnly"),GeometryOnly) || !GeometryOnly
            || !Receipt->TryGetStringField(TEXT("method"),Method) || Method!=TEXT("convex_halfspace_difference_source_corner_barycentrics")
            || !Receipt->TryGetStringField(TEXT("winding"),Winding) || Winding!=TEXT("preserve_input_index_order")
            || !Receipt->TryGetNumberField(TEXT("sourceTriangles"),SourceTriangles) || SourceTriangles!=SourceArrays.Indices.Num()/3
            || !Receipt->TryGetNumberField(TEXT("outputTriangles"),OutputTriangles) || OutputTriangles!=Arrays.Indices.Num()/3)
            return Reject(TEXT("unknown carve topology policy"));
        const TArray<TSharedPtr<FJsonValue>> *Touched=nullptr,*Removed=nullptr,*Boundary=nullptr;const TSharedPtr<FJsonObject>* Outside=nullptr;
        if (!Receipt->TryGetArrayField(TEXT("touchedSourceTriangles"),Touched) || !Receipt->TryGetArrayField(TEXT("fullyRemovedSourceTriangles"),Removed)
            || !Receipt->TryGetArrayField(TEXT("addedBoundaryVertices"),Boundary) || !Receipt->TryGetObjectField(TEXT("outsidePreservation"),Outside))
            return Reject(TEXT("missing bounded topology ledger"));
        TSet<int32> TouchedIds,RemovedIds;
        for (const auto& Row:*Touched) { int32 I; if (!JsonInteger(Row,I) || I<0 || I>=SourceTriangles || TouchedIds.Contains(I)) return Reject(TEXT("invalid touched face"));TouchedIds.Add(I); }
        for (const auto& Row:*Removed) { int32 I; if (!JsonInteger(Row,I) || !TouchedIds.Contains(I) || RemovedIds.Contains(I)) return Reject(TEXT("invalid removed face"));RemovedIds.Add(I); }
        const FVector Min(960,-4260,5980),Max(8460,4260,24000);
        TMap<int32,TArray<FCitadelCarveTriangle>> ExpectedTouched;
        for (int32 Triangle=0;Triangle<SourceTriangles;++Triangle)
        {
            FVector Corners[3];FBox Bounds(ForceInit);
            for (int32 Corner=0;Corner<3;++Corner)
            {Corners[Corner]=FVector(SourceArrays.Positions[SourceArrays.Indices[Triangle*3+Corner]]);Bounds+=Corners[Corner];}
            bool Exterior=false;
            for (int32 Axis=0;Axis<3;++Axis) Exterior|=Bounds.Max[Axis]<Min[Axis]-1e-7 || Bounds.Min[Axis]>Max[Axis]+1e-7;
            if (Exterior) {if (TouchedIds.Contains(Triangle)) return Reject(TEXT("an exterior source face was touched"));continue;}
            TArray<FCitadelCarveTriangle> Expected;bool ActualTouched=false;
            if (!ExpectedCarve(Corners,Min,Max,Expected,ActualTouched)) return Reject(TEXT("source face subtraction cannot be verified"));
            if (ActualTouched!=TouchedIds.Contains(Triangle)) return Reject(TEXT("touched face ledger differs from actual occupied subtraction"));
            if (!ActualTouched) continue;
            if (Expected.IsEmpty()!=RemovedIds.Contains(Triangle)) return Reject(TEXT("removed face ledger differs from actual occupied subtraction"));
            ExpectedTouched.Add(Triangle,MoveTemp(Expected));
        }
        for (int32 Triangle:RemovedIds)
            for (int32 Corner=0;Corner<3;++Corner)
            {
                const FVector Position(SourceArrays.Positions[SourceArrays.Indices[Triangle*3+Corner]]);
                for (int32 Axis=0;Axis<3;++Axis)
                    if (Position[Axis]<Min[Axis]-.01 || Position[Axis]>Max[Axis]+.01)
                        return Reject(TEXT("removed face retains exterior source area"));
            }
        for (int32 Triangle:TouchedIds)
        {
            FBox Bounds(ForceInit);for (int32 C=0;C<3;++C) Bounds+=FVector(SourceArrays.Positions[SourceArrays.Indices[Triangle*3+C]]);
            if (!Bounds.Intersect(FBox(Min,Max))) return Reject(TEXT("an exterior source face was touched"));
        }
        const TArray<TSharedPtr<FJsonValue>>* OutsideIds=nullptr;
        if (!(*Outside)->TryGetArrayField(TEXT("sourceTriangleIds"),OutsideIds)
            || OutsideIds->Num()+TouchedIds.Num()!=SourceTriangles) return Reject(TEXT("outside face ledger incomplete"));
        TSet<int32> OutsideSet;TMap<int32,int32> ExpectedOutputCounts;
        for (const auto& Row:*OutsideIds)
        {
            int32 I;if (!JsonInteger(Row,I) || I<0 || I>=SourceTriangles || TouchedIds.Contains(I) || OutsideSet.Contains(I)) return Reject(TEXT("invalid exterior source face"));
            OutsideSet.Add(I);ExpectedOutputCounts.Add(I,0);
        }
        TMap<int32,int32> BoundarySource;TMap<int32,FVector> BoundaryWeights;
        if (Arrays.Positions.Num()-SourceArrays.Positions.Num()!=Boundary->Num()) return Reject(TEXT("boundary corner ledger incomplete"));
        for (const auto& Row:*Boundary)
        {
            const TSharedPtr<FJsonObject>* BoundaryObject=nullptr;
            if (!Row->TryGetObject(BoundaryObject) || !BoundaryObject || !BoundaryObject->IsValid()) return Reject(TEXT("invalid boundary corner object"));
            const auto B=*BoundaryObject;const TArray<TSharedPtr<FJsonValue>> *Ids=nullptr,*Weights=nullptr;int32 Index;
            if (!JsonInteger(B->TryGetField(TEXT("index")),Index) || Index<SourceArrays.Positions.Num() || Index>=Arrays.Positions.Num()
                || BoundarySource.Contains(Index) || !B->TryGetArrayField(TEXT("sourceIndices"),Ids) || Ids->Num()!=3
                || !B->TryGetArrayField(TEXT("weights"),Weights) || Weights->Num()!=3) return Reject(TEXT("invalid boundary corner"));
            int32 Corners[3];double W[3],Sum=0;FVector Point=FVector::ZeroVector;
            for (int32 C=0;C<3;++C)
            {
                if (!JsonInteger((*Ids)[C],Corners[C]) || Corners[C]<0 || Corners[C]>=SourceArrays.Positions.Num()
                    || (*Weights)[C]->Type!=EJson::Number || !(*Weights)[C]->TryGetNumber(W[C]) || !FMath::IsFinite(W[C]) || W[C]<-1e-12 || W[C]>1+1e-12)
                    return Reject(TEXT("invalid boundary barycentrics"));
                Sum+=W[C];Point+=FVector(SourceArrays.Positions[Corners[C]])*W[C];
            }
            const int32 Triangle=Corners[0]/3;
            if (FMath::Abs(Sum-1)>1e-10 || !TouchedIds.Contains(Triangle) || Corners[0]!=Triangle*3 || Corners[1]!=Triangle*3+1 || Corners[2]!=Triangle*3+2
                || !FVector(Arrays.Positions[Index]).Equals(Point,.01)) return Reject(TEXT("boundary is not derived from its touched source face"));
            bool OnCutPlane=false;
            for (int32 Axis=0;Axis<3;++Axis)
                OnCutPlane|=FMath::Abs(Point[Axis]-Min[Axis])<=.01 || FMath::Abs(Point[Axis]-Max[Axis])<=.01;
            if (!OnCutPlane) return Reject(TEXT("new boundary corner is not on a measured carve plane"));
            FVector Normal=FVector::ZeroVector,Tangent=FVector::ZeroVector;FVector4 Color=FVector4(0,0,0,0);
            for (int32 C=0;C<3;++C)
            {
                Normal+=FVector(SourceArrays.Normals[Corners[C]])*W[C];
                if (!SourceArrays.Tangents.IsEmpty()) Tangent+=FVector(SourceArrays.Tangents[Corners[C]])*W[C];
                if (!SourceArrays.Colors.IsEmpty()) Color+=FVector4(SourceArrays.Colors[Corners[C]])*W[C];
            }
            if (!Normal.Normalize() || !FVector(Arrays.Normals[Index]).Equals(Normal,1e-5)) return Reject(TEXT("boundary source normal changed"));
            for (int32 U=0;U<Arrays.UVs.Num();++U)
            {
                FVector2D UV=FVector2D::ZeroVector;
                for (int32 C=0;C<3;++C) UV+=FVector2D(SourceArrays.UVs[U][Corners[C]])*W[C];
                if (!FVector2D(Arrays.UVs[U][Index]).Equals(UV,1e-5)) return Reject(TEXT("boundary UV interpolation changed"));
            }
            if (!SourceArrays.Colors.IsEmpty() && !FVector4(Arrays.Colors[Index]).Equals(Color,1e-5)) return Reject(TEXT("boundary color interpolation changed"));
            if (!SourceArrays.Tangents.IsEmpty())
            {
                bool AllZero=true;for (int32 C=0;C<3;++C) if (W[C]>1e-15 && SourceArrays.Tangents[Corners[C]].SizeSquared()!=0) AllZero=false;
                if (!AllZero) { Tangent-=Normal*FVector::DotProduct(Tangent,Normal);if (!Tangent.Normalize()) return Reject(TEXT("boundary tangent cannot retain its source plane")); }
                else Tangent=FVector::ZeroVector;
                if (!FVector(Arrays.Tangents[Index]).Equals(Tangent,1e-5)) return Reject(TEXT("boundary source tangent changed"));
            }
            if (!SourceArrays.Signs.IsEmpty())
            {
                TOptional<float> Sign;
                for (int32 C=0;C<3;++C) if (W[C]>1e-15)
                {
                    const float Value=SourceArrays.Signs[Corners[C]];
                    if (Sign.IsSet() && Sign.GetValue()!=Value) return Reject(TEXT("boundary crosses a handedness seam"));Sign=Value;
                }
                if (!Sign.IsSet() || Arrays.Signs[Index]!=Sign.GetValue()) return Reject(TEXT("boundary binormal sign changed"));
            }
            BoundarySource.Add(Index,Triangle);
            BoundaryWeights.Add(Index,FVector(W[0],W[1],W[2]));
        }
        int32 LastOrigin=INDEX_NONE;TMap<int32,int32> TouchedOutputCounts;TArray<int32> OutputOrigins;TSet<int32> UsedBoundary;
        for (int32 Offset=0;Offset<Arrays.Indices.Num();Offset+=3)
        {
            int32 Origin=INDEX_NONE;FVector P[3];
            for (int32 C=0;C<3;++C)
            {
                const int32 Index=Arrays.Indices[Offset+C];const int32 Face=Index<SourceArrays.Positions.Num()?Index/3:BoundarySource.FindChecked(Index);
                if (Origin!=INDEX_NONE && Origin!=Face) return Reject(TEXT("output face crosses source seams"));Origin=Face;P[C]=FVector(Arrays.Positions[Index]);
            }
            if (RemovedIds.Contains(Origin) || Arrays.Materials[Offset/3]!=SourceArrays.Materials[Origin]) return Reject(TEXT("output resurrects removed face or changes material"));
            if (Origin<LastOrigin) return Reject(TEXT("output reordered committed source faces"));LastOrigin=Origin;
            OutputOrigins.Add(Origin);
            const FVector A=FVector(SourceArrays.Positions[Origin*3]),B=FVector(SourceArrays.Positions[Origin*3+1]),C=FVector(SourceArrays.Positions[Origin*3+2]);
            const FVector FaceNormal=FVector::CrossProduct(P[1]-P[0],P[2]-P[0]);
            if (FaceNormal.IsNearlyZero(1e-10) || FVector::DotProduct(FaceNormal,FVector::CrossProduct(B-A,C-A))<=0) return Reject(TEXT("output changes winding or adds degenerate face"));
            if (OutsideSet.Contains(Origin))
            {
                ++ExpectedOutputCounts[Origin];for (int32 I=0;I<3;++I) if (Arrays.Indices[Offset+I]!=SourceArrays.Indices[Origin*3+I]) return Reject(TEXT("exterior face indices changed"));
            }
            else
            {
                const int32 ActualOrdinal=TouchedOutputCounts.FindOrAdd(Origin)++;
                const auto* Expected=ExpectedTouched.Find(Origin);
                if (!Expected || !Expected->IsValidIndex(ActualOrdinal)) return Reject(TEXT("exterior source fragment duplicated or invented"));
                for (int32 Corner=0;Corner<3;++Corner)
                {
                    const int32 Index=Arrays.Indices[Offset+Corner];FVector Weights;
                    if (Index<SourceArrays.Positions.Num())
                        Weights=Index%3==0?FVector(1,0,0):Index%3==1?FVector(0,1,0):FVector(0,0,1);
                    else {Weights=BoundaryWeights.FindChecked(Index);UsedBoundary.Add(Index);}
                    if (!Weights.Equals((*Expected)[ActualOrdinal].Weights[Corner],1e-10))
                        return Reject(TEXT("output does not cover exact deterministic exterior source fragments"));
                }
                bool Exterior=false;
                for (int32 Axis=0;Axis<3;++Axis)
                    Exterior|=(P[0][Axis]<=Min[Axis]+.01 && P[1][Axis]<=Min[Axis]+.01 && P[2][Axis]<=Min[Axis]+.01)
                        || (P[0][Axis]>=Max[Axis]-.01 && P[1][Axis]>=Max[Axis]-.01 && P[2][Axis]>=Max[Axis]-.01);
                if (!Exterior) return Reject(TEXT("clipped face remains inside the occupied hall"));
            }
        }
        for (const auto& Pair:ExpectedOutputCounts) if (Pair.Value!=1) return Reject(TEXT("exterior source face omitted or duplicated"));
        for (const auto& Pair:ExpectedTouched)
            if (TouchedOutputCounts.FindRef(Pair.Key)!=Pair.Value.Num()) return Reject(TEXT("exterior source fragments omitted"));
        if (UsedBoundary.Num()!=BoundarySource.Num()) return Reject(TEXT("boundary ledger contains unused invented corners"));
        for (int32 Lod=1;Lod<Source->GetNumSourceModels();++Lod)
        { FMeshDescription Other;if (Source->GetSourceModel(Lod).LoadMeshDescription(Other)) return Reject(TEXT("independently authored LOD requires its own carve")); }

        // Corner expansion is an interchange format, not native vertex connectivity.
        // Copy committed topology so recomputed exterior shading and orphan data survive.
        FMeshDescription Description;
        if (!Source->GetSourceModel(0).LoadMeshDescription(Description)) return Reject(TEXT("committed topology unavailable"));
        FStaticMeshAttributes Attr(Description);auto UVs=Attr.GetVertexInstanceUVs();
        const auto& OriginalGroups=Current->GetArrayField(TEXT("trianglePolygonGroupIds"));
        const auto& OriginalTriangles=Current->GetArrayField(TEXT("triangleIds"));
        const auto& OriginalInstances=Current->GetArrayField(TEXT("cornerVertexInstanceIds"));
        const auto& OriginalVertices=Current->GetArrayField(TEXT("cornerVertexIds"));
        TArray<FVertexInstanceID> Instances;Instances.SetNum(Arrays.Positions.Num());
        TMap<FVertexID,TArray<FEdgeID>> BoundarySupports;
        for (const FVertexID Vertex:Description.Vertices().GetElementIDs())
            BoundarySupports.Add(Vertex,TArray<FEdgeID>(Description.GetVertexConnectedEdgeIDs(Vertex)));
        int32 NextVertex=0,NextInstance=0,NextTriangle=0;
        for (const FVertexID Vertex:Description.Vertices().GetElementIDs()) NextVertex=FMath::Max(NextVertex,Vertex.GetValue()+1);
        for (const FVertexInstanceID Instance:Description.VertexInstances().GetElementIDs()) NextInstance=FMath::Max(NextInstance,Instance.GetValue()+1);
        for (const FTriangleID Triangle:Description.Triangles().GetElementIDs()) NextTriangle=FMath::Max(NextTriangle,Triangle.GetValue()+1);
        for (int32 I=0;I<SourceArrays.Positions.Num();++I)
            Instances[I]=FVertexInstanceID(int32(OriginalInstances[I]->AsNumber()));
        TMap<FEdgeID,TArray<TPair<FVector3f,FVertexID>>> EdgeBoundaryVertices;
        TMap<int32,TArray<TPair<FVector3f,FVertexID>>> FaceBoundaryVertices;
        for (int32 I=SourceArrays.Positions.Num();I<Arrays.Positions.Num();++I)
        {
            const int32 Origin=BoundarySource.FindChecked(I);const FVector Weights=BoundaryWeights.FindChecked(I);
            TArray<FVertexID> Support;
            for (int32 Corner=0;Corner<3;++Corner) if (Weights[Corner]>1e-12)
                Support.AddUnique(FVertexID(int32(OriginalVertices[Origin*3+Corner]->AsNumber())));
            FVertexID Vertex;TArray<FEdgeID> Edges;
            if (Support.Num()==1) {Vertex=Support[0];Edges=BoundarySupports.FindChecked(Vertex);}
            else
            {
                TArray<TPair<FVector3f,FVertexID>>* Candidates=nullptr;
                if (Support.Num()==2)
                {
                    const FEdgeID Edge=Description.GetVertexPairEdge(Support[0],Support[1]);
                    if (!Description.IsEdgeValid(Edge)) return Reject(TEXT("boundary source edge connectivity unavailable"));
                    Edges.Add(Edge);Candidates=&EdgeBoundaryVertices.FindOrAdd(Edge);
                }
                else Candidates=&FaceBoundaryVertices.FindOrAdd(Origin);
                const auto* Existing=Candidates->FindByPredicate([&Arrays,I](const auto& Row){return Row.Key==Arrays.Positions[I];});
                if (Existing) Vertex=Existing->Value;
                else
                {
                    Vertex=FVertexID(NextVertex++);Description.CreateVertexWithID(Vertex);
                    Attr.GetVertexPositions()[Vertex]=Arrays.Positions[I];Candidates->Emplace(Arrays.Positions[I],Vertex);
                    BoundarySupports.Add(Vertex,Edges);
                }
            }
            const FVertexInstanceID Instance(NextInstance++);Description.CreateVertexInstanceWithID(Instance,Vertex);Instances[I]=Instance;
            Attr.GetVertexInstanceNormals()[Instance]=Arrays.Normals[I];
            for (int32 U=0;U<Arrays.UVs.Num();++U) UVs.Set(Instance,U,Arrays.UVs[U][I]);
            if (!Arrays.Colors.IsEmpty()) Attr.GetVertexInstanceColors()[Instance]=Arrays.Colors[I];
            if (!Arrays.Tangents.IsEmpty()) Attr.GetVertexInstanceTangents()[Instance]=Arrays.Tangents[I];
            if (!Arrays.Signs.IsEmpty()) Attr.GetVertexInstanceBinormalSigns()[Instance]=Arrays.Signs[I];
        }
        for (int32 Origin:TouchedIds)
            Description.DeleteTriangle(FTriangleID(int32(OriginalTriangles[Origin]->AsNumber())));
        TSet<int32> Replaced;
        for (int32 I=0;I<Arrays.Indices.Num();I+=3)
        {
            const int32 Origin=OutputOrigins[I/3];if (!TouchedIds.Contains(Origin)) continue;
            const TArray<FVertexInstanceID> Corners={Instances[Arrays.Indices[I]],Instances[Arrays.Indices[I+1]],Instances[Arrays.Indices[I+2]]};
            const FTriangleID Triangle(Replaced.Contains(Origin)?NextTriangle++:int32(OriginalTriangles[Origin]->AsNumber()));Replaced.Add(Origin);
            TArray<FEdgeID> CreatedEdges;
            Description.CreateTriangleWithID(Triangle,FPolygonGroupID(int32(OriginalGroups[Origin]->AsNumber())),Corners,&CreatedEdges);
            for (const FEdgeID Edge:CreatedEdges)
            {
                const auto Ends=Description.GetEdgeVertices(Edge);
                const auto& A=BoundarySupports.FindChecked(Ends[0]);const auto& B=BoundarySupports.FindChecked(Ends[1]);
                for (const FEdgeID OriginalEdge:A) if (B.Contains(OriginalEdge))
                    Attr.GetEdgeHardnesses()[Edge]=Attr.GetEdgeHardnesses()[OriginalEdge];
            }
        }
        UPackage* Package=CreatePackage(*PackageName);
        UStaticMesh* Target=DuplicateObject<UStaticMesh>(Source,Package,*Name);
        if (!Target) return Reject(TEXT("native clone allocation failed"));
        Target->SetFlags(RF_Public|RF_Standalone);Target->ClearFlags(RF_Transient);
        Target->CreateMeshDescription(0,MoveTemp(Description));Target->CommitMeshDescription(0);
        TArray<FText> Errors;Target->Build(true,&Errors);
        if (!Errors.IsEmpty() || !Target->GetRenderData()) return Reject(TEXT("native cloned terrain build failed; retain partial private package"));
        if (auto* Body=Target->GetBodySetup()) { Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes(); }
        Package->GetMetaData().SetValue(Target,TEXT("WarCapitalTerrain"),*(Collection+TEXT(":")+Name));
        Package->GetMetaData().SetValue(Target,TEXT("WarCitadelTerrainSource"),*Source->GetPathName());
        Package->GetMetaData().SetValue(Target,TEXT("WarCitadelTerrainSourceSha256"),*ExpectedHash);
        FAssetRegistryModule::AssetCreated(Target);Target->MarkPackageDirty();return Target;
    }
}

UStaticMesh* UWarImportLibrary::CreateCarvedCitadelTerrain(UStaticMesh* SourceMesh,const FString& Collection,const FString& ClippedJson)
{ return ImportCarvedTerrain(SourceMesh,Collection,ClippedJson,false); }
#if WITH_DEV_AUTOMATION_TESTS
UStaticMesh* UWarImportLibrary::CreateCarvedCitadelTerrainForAutomation(UStaticMesh* SourceMesh,const FString& Collection,const FString& ClippedJson)
{
    if (!IsValid(SourceMesh) || !SourceMesh->HasAnyFlags(RF_Transient)
        || !SourceMesh->GetOutermost()->GetName().StartsWith(TEXT("/Game/WorldRebuild/CitadelCarveAutomation/"))
        || FPackageName::DoesPackageExist(SourceMesh->GetOutermost()->GetName())) return nullptr;
    return ImportCarvedTerrain(SourceMesh,Collection,ClippedJson,true);
}
#endif

FString UWarImportLibrary::DescribeStaticMeshSourceData(UStaticMesh* Mesh, int32 Lod)
{
    auto Report = MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"), 1);
    Report->SetBoolField(TEXT("readOnly"), true);
    Report->SetBoolField(TEXT("available"), false);
    Report->SetBoolField(TEXT("valid"), false);
    Report->SetNumberField(TEXT("lod"), Lod);
    Report->SetStringField(TEXT("sourcePolicy"), TEXT("committed_mesh_description_bulk_data_no_working_copy"));
    Report->SetStringField(TEXT("coordinateSpace"), TEXT("mesh_local_cm"));
    Report->SetStringField(TEXT("triangleOrder"), TEXT("native_triangle_ids_and_corner_order"));
    const auto Serialize = [&Report]()
    {
        FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json)); return Json;
    };
    if (!IsValid(Mesh)) { Report->SetStringField(TEXT("reason"), TEXT("missingMesh")); return Serialize(); }
    Report->SetStringField(TEXT("mesh"), Mesh->GetPathName());
    if (Lod < 0 || Lod >= Mesh->GetNumSourceModels())
    { Report->SetStringField(TEXT("reason"), TEXT("missingSourceLod")); return Serialize(); }
    // Load committed bulk into a local description. Clone/Get can prefer uncommitted editor changes.
    FMeshDescription Description;
    if (!Mesh->GetSourceModel(Lod).LoadMeshDescription(Description))
    { Report->SetStringField(TEXT("reason"), TEXT("missingCommittedMeshDescription")); return Serialize(); }
    const FStaticMeshConstAttributes Attributes(Description);
    const auto Positions = Attributes.GetVertexPositions();
    const auto Normals = Attributes.GetVertexInstanceNormals();
    const auto UVs = Attributes.GetVertexInstanceUVs();
    const auto Slots = Attributes.GetPolygonGroupMaterialSlotNames();
    const auto Colors = Attributes.GetVertexInstanceColors();
    const auto Tangents = Attributes.GetVertexInstanceTangents();
    const auto Signs = Attributes.GetVertexInstanceBinormalSigns();
    if (!Positions.IsValid() || !Normals.IsValid() || !UVs.IsValid() || !Slots.IsValid() || UVs.GetNumChannels() < 1)
    { Report->SetStringField(TEXT("reason"), TEXT("missingRequiredSourceAttributes")); return Serialize(); }

    int32 Invalid = 0;
    const auto Number = [&Invalid](double Value) -> TSharedPtr<FJsonValue>
    {
        if (FMath::IsFinite(Value)) return MakeShared<FJsonValueNumber>(Value);
        ++Invalid; return MakeShared<FJsonValueNull>();
    };
    const auto Vector3 = [&Number](const FVector3f& Value) -> TSharedPtr<FJsonValue>
    { return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(Value.X),Number(Value.Y),Number(Value.Z)}); };
    const auto Vector2 = [&Number](const FVector2f& Value) -> TSharedPtr<FJsonValue>
    { return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(Value.X),Number(Value.Y)}); };
    TArray<TSharedPtr<FJsonValue>> MaterialRows, GroupRows;
    TMap<FPolygonGroupID, int32> GroupMaterials;
    const auto& Materials = Mesh->GetStaticMaterials();
    for (int32 Index = 0; Index < Materials.Num(); ++Index)
    {
        const auto& Material = Materials[Index]; auto Row = MakeShared<FJsonObject>();
        Row->SetNumberField(TEXT("index"), Index);
        Row->SetStringField(TEXT("slotName"), Material.MaterialSlotName.ToString());
        Row->SetStringField(TEXT("importedSlotName"), Material.ImportedMaterialSlotName.ToString());
        if (Material.MaterialInterface) Row->SetStringField(TEXT("material"), Material.MaterialInterface->GetPathName());
        else Row->SetField(TEXT("material"), MakeShared<FJsonValueNull>());
        MaterialRows.Add(MakeShared<FJsonValueObject>(Row));
    }
    for (const FPolygonGroupID Group : Description.PolygonGroups().GetElementIDs())
    {
        const FName Slot = Slots[Group];
        int32 Index = Materials.IndexOfByPredicate([Slot](const FStaticMaterial& M) { return M.ImportedMaterialSlotName == Slot; });
        if (Index == INDEX_NONE)
            Index = Materials.IndexOfByPredicate([Slot](const FStaticMaterial& M) { return M.MaterialSlotName == Slot; });
        if (Index == INDEX_NONE) ++Invalid;
        GroupMaterials.Add(Group, Index); auto Row = MakeShared<FJsonObject>();
        Row->SetNumberField(TEXT("id"), Group.GetValue()); Row->SetStringField(TEXT("slotName"), Slot.ToString());
        Row->SetNumberField(TEXT("materialIndex"), Index); GroupRows.Add(MakeShared<FJsonValueObject>(Row));
    }
    TArray<TSharedPtr<FJsonValue>> ExpandedPositions, ExpandedNormals, Indices, TriangleMaterials;
    TArray<TSharedPtr<FJsonValue>> ExpandedColors, ExpandedTangents, ExpandedSigns;
    TArray<TSharedPtr<FJsonValue>> TriangleIds, PolygonIds, GroupIds, VertexIds, InstanceIds;
    TArray<TArray<TSharedPtr<FJsonValue>>> Channels; Channels.SetNum(UVs.GetNumChannels());
    for (const FTriangleID Triangle : Description.Triangles().GetElementIDs())
    {
        const FPolygonGroupID Group = Description.GetTrianglePolygonGroup(Triangle);
        const auto Corners = Description.GetTriangleVertexInstances(Triangle);
        TriangleIds.Add(Number(Triangle.GetValue())); PolygonIds.Add(Number(Description.GetTrianglePolygon(Triangle).GetValue()));
        GroupIds.Add(Number(Group.GetValue())); TriangleMaterials.Add(Number(GroupMaterials.FindChecked(Group)));
        for (const FVertexInstanceID Corner : Corners)
        {
            const FVertexID Vertex = Description.GetVertexInstanceVertex(Corner);
            Indices.Add(Number(ExpandedPositions.Num())); ExpandedPositions.Add(Vector3(Positions[Vertex]));
            ExpandedNormals.Add(Vector3(Normals[Corner])); VertexIds.Add(Number(Vertex.GetValue())); InstanceIds.Add(Number(Corner.GetValue()));
            for (int32 Channel = 0; Channel < Channels.Num(); ++Channel) Channels[Channel].Add(Vector2(UVs.Get(Corner, Channel)));
            if (Colors.IsValid())
            {
                const FVector4f Color = Colors[Corner];
                ExpandedColors.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
                    Number(Color.X),Number(Color.Y),Number(Color.Z),Number(Color.W)}));
            }
            if (Tangents.IsValid()) ExpandedTangents.Add(Vector3(Tangents[Corner]));
            if (Signs.IsValid()) ExpandedSigns.Add(Number(Signs[Corner]));
        }
    }
    auto Data = MakeShared<FJsonObject>();
    Data->SetArrayField(TEXT("positions"), ExpandedPositions); Data->SetArrayField(TEXT("indices"), Indices);
    Data->SetArrayField(TEXT("normals"), ExpandedNormals); Data->SetArrayField(TEXT("uvs"), Channels[0]);
    Data->SetArrayField(TEXT("triangleMaterials"), TriangleMaterials);
    TArray<TSharedPtr<FJsonValue>> ChannelRows;
    for (const auto& Channel : Channels) ChannelRows.Add(MakeShared<FJsonValueArray>(Channel));
    Data->SetArrayField(TEXT("uvChannels"), ChannelRows);
    if (Colors.IsValid()) Data->SetArrayField(TEXT("vertexColors"), ExpandedColors);
    if (Tangents.IsValid()) Data->SetArrayField(TEXT("tangents"), ExpandedTangents);
    if (Signs.IsValid()) Data->SetArrayField(TEXT("binormalSigns"), ExpandedSigns);
    Report->SetStringField(TEXT("optionalAttributePolicy"), TEXT("stored_registered_values_authorship_not_inferred"));
    Report->SetObjectField(TEXT("data"), Data); Report->SetArrayField(TEXT("materialSlots"), MaterialRows);
    Report->SetArrayField(TEXT("polygonGroups"), GroupRows); Report->SetArrayField(TEXT("triangleIds"), TriangleIds);
    Report->SetArrayField(TEXT("trianglePolygonIds"), PolygonIds); Report->SetArrayField(TEXT("trianglePolygonGroupIds"), GroupIds);
    Report->SetArrayField(TEXT("cornerVertexIds"), VertexIds); Report->SetArrayField(TEXT("cornerVertexInstanceIds"), InstanceIds);
    Report->SetNumberField(TEXT("sourceVertexCount"), Description.Vertices().Num());
    Report->SetNumberField(TEXT("sourceVertexInstanceCount"), Description.VertexInstances().Num());
    Report->SetNumberField(TEXT("sourceTriangleCount"), Description.Triangles().Num());
    Report->SetNumberField(TEXT("invalidValues"), Invalid);
    Report->SetBoolField(TEXT("available"), true);
    Report->SetBoolField(TEXT("valid"), Invalid == 0 && !Indices.IsEmpty());
    return Serialize();
}

FString UWarImportLibrary::DescribeStaticMeshStoredCorners(UStaticMesh* Mesh,int32 Lod)
{
    auto Report=MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"),1);Report->SetBoolField(TEXT("readOnly"),true);
    Report->SetBoolField(TEXT("available"),false);Report->SetBoolField(TEXT("valid"),false);
    Report->SetNumberField(TEXT("lod"),Lod);
    Report->SetStringField(TEXT("sourcePolicy"),TEXT("committed_mesh_description_bulk_data_no_working_copy"));
    Report->SetStringField(TEXT("cornerPolicy"),TEXT("all_stored_vertex_instances_in_native_id_order_including_unused"));
    Report->SetStringField(TEXT("optionalAttributePolicy"),TEXT("stored_registered_values_authorship_not_inferred"));
    const auto Serialize=[&Report]()
    {FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));return Json;};
    if (!IsValid(Mesh)) {Report->SetStringField(TEXT("reason"),TEXT("missingMesh"));return Serialize();}
    Report->SetStringField(TEXT("mesh"),Mesh->GetPathName());
    if (Lod<0 || Lod>=Mesh->GetNumSourceModels())
    {Report->SetStringField(TEXT("reason"),TEXT("missingSourceLod"));return Serialize();}
    FMeshDescription Description;
    if (!Mesh->GetSourceModel(Lod).LoadMeshDescription(Description))
    {Report->SetStringField(TEXT("reason"),TEXT("missingCommittedMeshDescription"));return Serialize();}
    const FStaticMeshConstAttributes Attr(Description);
    const auto Positions=Attr.GetVertexPositions();const auto Normals=Attr.GetVertexInstanceNormals();const auto Tangents=Attr.GetVertexInstanceTangents();
    const auto UVs=Attr.GetVertexInstanceUVs();const auto Colors=Attr.GetVertexInstanceColors();const auto Signs=Attr.GetVertexInstanceBinormalSigns();
    if (!Positions.IsValid() || !Normals.IsValid() || !UVs.IsValid() || UVs.GetNumChannels()<1)
    {Report->SetStringField(TEXT("reason"),TEXT("missingRequiredSourceAttributes"));return Serialize();}
    int32 Invalid=0;
    const auto Number=[&Invalid](double Value)->TSharedPtr<FJsonValue>
    {if (FMath::IsFinite(Value)) return MakeShared<FJsonValueNumber>(Value);++Invalid;return MakeShared<FJsonValueNull>();};
    const auto Vector3=[&Number](const FVector3f& Value)->TSharedPtr<FJsonValue>
    {return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(Value.X),Number(Value.Y),Number(Value.Z)});};
    TArray<TSharedPtr<FJsonValue>> InstanceIds,VertexIds,Points,NormalRows,TangentRows,ColorRows,SignRows;
    TArray<TArray<TSharedPtr<FJsonValue>>> Channels;Channels.SetNum(UVs.GetNumChannels());
    for (const FVertexInstanceID Corner:Description.VertexInstances().GetElementIDs())
    {
        const FVertexID Vertex=Description.GetVertexInstanceVertex(Corner);
        InstanceIds.Add(Number(Corner.GetValue()));VertexIds.Add(Number(Vertex.GetValue()));
        Points.Add(Vector3(Positions[Vertex]));NormalRows.Add(Vector3(Normals[Corner]));
        for (int32 Channel=0;Channel<Channels.Num();++Channel)
        {const FVector2f UV=UVs.Get(Corner,Channel);Channels[Channel].Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(UV.X),Number(UV.Y)}));}
        if (Tangents.IsValid()) TangentRows.Add(Vector3(Tangents[Corner]));
        if (Colors.IsValid())
        {const FVector4f Color=Colors[Corner];ColorRows.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(Color.X),Number(Color.Y),Number(Color.Z),Number(Color.W)}));}
        if (Signs.IsValid()) SignRows.Add(Number(Signs[Corner]));
    }
    auto Data=MakeShared<FJsonObject>();Data->SetArrayField(TEXT("positions"),Points);Data->SetArrayField(TEXT("normals"),NormalRows);
    Data->SetArrayField(TEXT("uvs"),Channels[0]);
    TArray<TSharedPtr<FJsonValue>> ChannelRows;
    for (const auto& Channel:Channels) ChannelRows.Add(MakeShared<FJsonValueArray>(Channel));
    Data->SetArrayField(TEXT("uvChannels"),ChannelRows);
    if (Tangents.IsValid()) Data->SetArrayField(TEXT("tangents"),TangentRows);
    if (Colors.IsValid()) Data->SetArrayField(TEXT("vertexColors"),ColorRows);
    if (Signs.IsValid()) Data->SetArrayField(TEXT("binormalSigns"),SignRows);
    Report->SetObjectField(TEXT("data"),Data);Report->SetArrayField(TEXT("instanceIds"),InstanceIds);Report->SetArrayField(TEXT("vertexIds"),VertexIds);
    auto Topology=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Vertices,Edges,Triangles;
    for (const FVertexID Vertex:Description.Vertices().GetElementIDs())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("id"),Vertex.GetValue());
        Row->SetField(TEXT("position"),Vector3(Positions[Vertex]));Vertices.Add(MakeShared<FJsonValueObject>(Row));
    }
    for (const FEdgeID Edge:Description.Edges().GetElementIDs())
    {
        auto Row=MakeShared<FJsonObject>();const auto Ends=Description.GetEdgeVertices(Edge);
        Row->SetNumberField(TEXT("id"),Edge.GetValue());Row->SetArrayField(TEXT("vertices"),{Number(Ends[0].GetValue()),Number(Ends[1].GetValue())});
        Row->SetBoolField(TEXT("hard"),Attr.GetEdgeHardnesses()[Edge]);Edges.Add(MakeShared<FJsonValueObject>(Row));
    }
    for (const FTriangleID Triangle:Description.Triangles().GetElementIDs())
    {
        auto Row=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Corners,TriangleEdges;
        for (const FVertexInstanceID Instance:Description.GetTriangleVertexInstances(Triangle)) Corners.Add(Number(Instance.GetValue()));
        for (const FEdgeID Edge:Description.GetTriangleEdges(Triangle)) TriangleEdges.Add(Number(Edge.GetValue()));
        Row->SetNumberField(TEXT("id"),Triangle.GetValue());Row->SetNumberField(TEXT("polygonId"),Description.GetTrianglePolygon(Triangle).GetValue());
        Row->SetNumberField(TEXT("groupId"),Description.GetTrianglePolygonGroup(Triangle).GetValue());
        Row->SetArrayField(TEXT("instances"),Corners);Row->SetArrayField(TEXT("edges"),TriangleEdges);Triangles.Add(MakeShared<FJsonValueObject>(Row));
    }
    Topology->SetArrayField(TEXT("vertices"),Vertices);Topology->SetArrayField(TEXT("edges"),Edges);Topology->SetArrayField(TEXT("triangles"),Triangles);
    Report->SetObjectField(TEXT("topology"),Topology);
    Report->SetNumberField(TEXT("sourceVertexCount"),Description.Vertices().Num());
    Report->SetNumberField(TEXT("sourceVertexInstanceCount"),Description.VertexInstances().Num());
    Report->SetNumberField(TEXT("sourceTriangleCount"),Description.Triangles().Num());
    Report->SetNumberField(TEXT("invalidValues"),Invalid);Report->SetBoolField(TEXT("available"),true);
    Report->SetBoolField(TEXT("valid"),Invalid==0 && !InstanceIds.IsEmpty());return Serialize();
}

FString UWarImportLibrary::DescribeStaticMeshRenderedFaces(UStaticMesh* Mesh,int32 Lod)
{
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("schemaVersion"),1);
    Report->SetBoolField(TEXT("readOnly"),true);Report->SetBoolField(TEXT("available"),false);Report->SetBoolField(TEXT("valid"),false);
    Report->SetStringField(TEXT("mesh"),Mesh?Mesh->GetPathName():FString());Report->SetNumberField(TEXT("lod"),Lod);
    Report->SetStringField(TEXT("policy"),TEXT("actual_render_index_order_oriented_triangle_corners"));
    const auto Serialize=[&Report]() {FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));return Text;};
    const auto* Render=Mesh?Mesh->GetRenderData():nullptr;
    if (!Render || !Render->LODResources.IsValidIndex(Lod)) {Report->SetStringField(TEXT("reason"),TEXT("missingRenderLod"));return Serialize();}
    const auto& Resource=Render->LODResources[Lod];const auto& Buffer=Resource.VertexBuffers.StaticMeshVertexBuffer;
    const auto& Positions=Resource.VertexBuffers.PositionVertexBuffer;
    if (!Buffer.GetNumVertices() || !Buffer.GetNumTexCoords() || !Positions.GetVertexData()
        || !Buffer.GetTangentData() || !Buffer.GetTexCoordData() || !Resource.IndexBuffer.GetNumIndices() || !Resource.IndexBuffer.GetIndexDataSize())
    {Report->SetStringField(TEXT("reason"),TEXT("renderBuffersNotCpuReadable"));return Serialize();}
    int32 Invalid=0;
    const auto Number=[&Invalid](double Value)->TSharedPtr<FJsonValue>
    {if (FMath::IsFinite(Value)) return MakeShared<FJsonValueNumber>(Value);++Invalid;return MakeShared<FJsonValueNull>();};
    const auto V3=[&Number](FVector3f V)->TSharedPtr<FJsonValue>
    {return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(V.X),Number(V.Y),Number(V.Z)});};
    TArray<TSharedPtr<FJsonValue>> Faces;
    for (int32 SectionIndex=0;SectionIndex<Resource.Sections.Num();++SectionIndex)
    {
        const auto& Section=Resource.Sections[SectionIndex];
        for (uint32 Face=0;Face<Section.NumTriangles;++Face)
        {
            auto Row=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Ids,Points,Normals,Tangents,Binormals,Channels;
            TArray<TArray<TSharedPtr<FJsonValue>>> UVs;UVs.SetNum(Buffer.GetNumTexCoords());
            for (uint32 C=0;C<3;++C)
            {
                const uint32 Vertex=Resource.IndexBuffer.GetIndex(Section.FirstIndex+Face*3+C);
                if (Vertex>=Buffer.GetNumVertices() || Vertex>=Positions.GetNumVertices())
                {Report->SetStringField(TEXT("reason"),TEXT("invalidRenderIndex"));return Serialize();}
                Ids.Add(Number(Vertex));Points.Add(V3(Positions.VertexPosition(Vertex)));Normals.Add(V3(FVector3f(Buffer.VertexTangentZ(Vertex))));
                Tangents.Add(V3(FVector3f(Buffer.VertexTangentX(Vertex))));Binormals.Add(V3(FVector3f(Buffer.VertexTangentY(Vertex))));
                for (uint32 U=0;U<Buffer.GetNumTexCoords();++U)
                {const FVector2f UV=Buffer.GetVertexUV(Vertex,U);UVs[U].Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{Number(UV.X),Number(UV.Y)}));}
            }
            for (const auto& Channel:UVs) Channels.Add(MakeShared<FJsonValueArray>(Channel));
            Row->SetNumberField(TEXT("index"),Section.FirstIndex/3+Face);Row->SetNumberField(TEXT("section"),SectionIndex);
            Row->SetNumberField(TEXT("materialIndex"),Section.MaterialIndex);Row->SetArrayField(TEXT("vertexIds"),Ids);
            Row->SetArrayField(TEXT("positions"),Points);Row->SetArrayField(TEXT("normals"),Normals);Row->SetArrayField(TEXT("tangents"),Tangents);
            Row->SetArrayField(TEXT("binormals"),Binormals);Row->SetArrayField(TEXT("uvChannels"),Channels);Faces.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
    Report->SetNumberField(TEXT("uvChannels"),Buffer.GetNumTexCoords());Report->SetNumberField(TEXT("invalidValues"),Invalid);
    Report->SetArrayField(TEXT("triangles"),Faces);Report->SetBoolField(TEXT("available"),true);Report->SetBoolField(TEXT("valid"),Invalid==0 && !Faces.IsEmpty());return Serialize();
}

FString UWarImportLibrary::DescribeStaticMeshNativePolicy(UStaticMesh* Mesh)
{
    auto Report = MakeShared<FJsonObject>(); Report->SetNumberField(TEXT("schemaVersion"), 1);
    Report->SetBoolField(TEXT("readOnly"), true); Report->SetBoolField(TEXT("available"), false); Report->SetBoolField(TEXT("valid"), false);
    Report->SetStringField(TEXT("mesh"), Mesh ? Mesh->GetPathName() : FString());
    Report->SetStringField(TEXT("policySource"), TEXT("native_persistent_accessors_and_full_reflected_source_structs"));
    FString Error;
    auto Policy = MakeShared<FJsonObject>(); auto MeshPolicy = MakeShared<FJsonObject>(); auto BodyPolicy = MakeShared<FJsonObject>();
    if (!Mesh || Mesh->GetNumSourceModels() < 1 || Mesh->GetNumSourceModels() > 8 || !Mesh->GetBodySetup())
        Error = TEXT("Committed mesh source models and persistent BodySetup are required.");
    else
    {
        TArray<TSharedPtr<FJsonValue>> Builds, Reductions;
        for (int32 Lod = 0; Lod < Mesh->GetNumSourceModels(); ++Lod)
        {
            const auto& Source = Mesh->GetSourceModel(Lod); auto Build = MakeShared<FJsonObject>(); auto Reduction = MakeShared<FJsonObject>();
            if (!FJsonObjectConverter::UStructToJsonObject(FMeshBuildSettings::StaticStruct(), &Source.BuildSettings, Build, 0, 0)
                || !FJsonObjectConverter::UStructToJsonObject(FMeshReductionSettings::StaticStruct(), &Source.ReductionSettings, Reduction, 0, 0))
            { Error = TEXT("An actual full source build/reduction struct could not be serialized."); break; }
            Builds.Add(MakeShared<FJsonValueObject>(Build)); Reductions.Add(MakeShared<FJsonValueObject>(Reduction));
        }
        auto Nanite = MakeShared<FJsonObject>(); auto Scale = MakeShared<FJsonObject>(); auto Slope = MakeShared<FJsonObject>();
        const auto* Body = Mesh->GetBodySetup(); const auto& NaniteSettings = Mesh->GetNaniteSettings();
        if (!FJsonObjectConverter::UStructToJsonObject(FMeshNaniteSettings::StaticStruct(), &NaniteSettings, Nanite, 0, 0)
            || !FJsonObjectConverter::UStructToJsonObject(TBaseStructure<FVector>::Get(), &Body->BuildScale3D, Scale, 0, 0)
            || !FJsonObjectConverter::UStructToJsonObject(FWalkableSlopeOverride::StaticStruct(), &Body->WalkableSlopeOverride, Slope, 0, 0))
            Error = TEXT("Actual Nanite or persistent collision structs could not be serialized.");
        Policy->SetNumberField(TEXT("sourceLods"), Mesh->GetNumSourceModels());
        Policy->SetArrayField(TEXT("buildSettings"), Builds); Policy->SetArrayField(TEXT("reductionSettings"), Reductions);
        MeshPolicy->SetBoolField(TEXT("allow_cpu_access"), Mesh->bAllowCPUAccess);
        MeshPolicy->SetBoolField(TEXT("auto_compute_lod_screen_size"), Mesh->GetAutoComputeLODScreenSize());
        MeshPolicy->SetNumberField(TEXT("light_map_coordinate_index"), Mesh->GetLightMapCoordinateIndex());
        MeshPolicy->SetNumberField(TEXT("light_map_resolution"), Mesh->GetLightMapResolution());
        MeshPolicy->SetNumberField(TEXT("lod_for_collision"), Mesh->LODForCollision);
        MeshPolicy->SetStringField(TEXT("lod_group"), Mesh->GetLODGroup().ToString());
        MeshPolicy->SetObjectField(TEXT("nanite_settings"), Nanite);
        BodyPolicy->SetNumberField(TEXT("collision_trace_flag"), int32(Body->CollisionTraceFlag));
        BodyPolicy->SetBoolField(TEXT("double_sided_geometry"), Body->bDoubleSidedGeometry);
        BodyPolicy->SetNumberField(TEXT("physics_type"), int32(Body->PhysicsType));
        BodyPolicy->SetNumberField(TEXT("collision_reponse"), int32(Body->CollisionReponse));
        BodyPolicy->SetBoolField(TEXT("generate_mirrored_collision"), Body->bGenerateMirroredCollision);
        BodyPolicy->SetBoolField(TEXT("generate_non_mirrored_collision"), Body->bGenerateNonMirroredCollision);
        BodyPolicy->SetObjectField(TEXT("build_scale3d"), Scale); BodyPolicy->SetObjectField(TEXT("walkable_slope_override"), Slope);
        BodyPolicy->SetStringField(TEXT("phys_material"), Body->PhysMaterial ? Body->PhysMaterial->GetPathName() : FString());
        Policy->SetObjectField(TEXT("mesh"), MeshPolicy); Policy->SetObjectField(TEXT("bodySetup"), BodyPolicy);
        Report->SetObjectField(TEXT("policy"), Policy);
        Report->SetBoolField(TEXT("available"), true); Report->SetBoolField(TEXT("valid"), Error.IsEmpty());
    }
    if (!Error.IsEmpty()) Report->SetStringField(TEXT("error"), Error);
    FString Text; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text)); return Text;
}

FString UWarImportLibrary::DescribeMaterialRoots(UMaterial* Material)
{
    auto Report=MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"),1);Report->SetBoolField(TEXT("readOnly"),true);
    Report->SetBoolField(TEXT("available"),false);
    if (IsInGameThread() && IsValid(Material))
    {
        const TPair<const TCHAR*,EMaterialProperty> Properties[]={
            {TEXT("MP_BASE_COLOR"),MP_BaseColor},{TEXT("MP_NORMAL"),MP_Normal},
            {TEXT("MP_ROUGHNESS"),MP_Roughness},{TEXT("MP_METALLIC"),MP_Metallic},
            {TEXT("MP_SPECULAR"),MP_Specular},{TEXT("MP_AMBIENT_OCCLUSION"),MP_AmbientOcclusion},
            {TEXT("MP_EMISSIVE_COLOR"),MP_EmissiveColor},{TEXT("MP_WORLD_POSITION_OFFSET"),MP_WorldPositionOffset},
            {TEXT("MP_OPACITY"),MP_Opacity},{TEXT("MP_OPACITY_MASK"),MP_OpacityMask},
            {TEXT("MP_MATERIAL_ATTRIBUTES"),MP_MaterialAttributes},{TEXT("MP_PIXEL_DEPTH_OFFSET"),MP_PixelDepthOffset},
            {TEXT("MP_DISPLACEMENT"),MP_Displacement},
            {TEXT("MP_CUSTOMIZED_UVS0"),MP_CustomizedUVs0},{TEXT("MP_CUSTOMIZED_UVS1"),MP_CustomizedUVs1},
            {TEXT("MP_CUSTOMIZED_UVS2"),MP_CustomizedUVs2},{TEXT("MP_CUSTOMIZED_UVS3"),MP_CustomizedUVs3},
            {TEXT("MP_CUSTOMIZED_UVS4"),MP_CustomizedUVs4},{TEXT("MP_CUSTOMIZED_UVS5"),MP_CustomizedUVs5},
            {TEXT("MP_CUSTOMIZED_UVS6"),MP_CustomizedUVs6},{TEXT("MP_CUSTOMIZED_UVS7"),MP_CustomizedUVs7}};
        auto Roots=MakeShared<FJsonObject>();bool bValid=true;
        for (const auto& Property:Properties)
        {
            const FExpressionInput* Input=Material->GetExpressionInputForProperty(Property.Value);
            if (!Input || (Input->Expression && !IsValid(Input->Expression))) { bValid=false;break; }
            Roots->SetObjectField(Property.Key,MaterialInputJson(*Input));
        }
        if (bValid)
        {
            Report->SetBoolField(TEXT("available"),true);
            Report->SetStringField(TEXT("material"),Material->GetPathName());
            Report->SetObjectField(TEXT("roots"),Roots);
        }
    }
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));return Json;
}

FString UWarImportLibrary::DescribeStaticMeshLumenResources(UStaticMesh* Mesh)
{
    const auto Json=[](const TSharedRef<FJsonObject>& Value)
    {
        FString Result;
        FJsonSerializer::Serialize(Value,TJsonWriterFactory<>::Create(&Result));
        return Result;
    };
    auto J=MakeShared<FJsonObject>();
    J->SetBoolField(TEXT("diagnosticOnly"),true);
    J->SetBoolField(TEXT("readOnly"),true);
    J->SetBoolField(TEXT("rendererStateVerified"),false);
    J->SetBoolField(TEXT("available"),false);
    if (!IsInGameThread() || !IsValid(Mesh)) return Json(J);
    J->SetStringField(TEXT("mesh"),Mesh->GetPathName());
    J->SetBoolField(TEXT("compiling"),Mesh->IsCompiling());
    if (Mesh->IsCompiling()) return Json(J);
    const FStaticMeshRenderData* Data=Mesh->GetRenderData();
    if (!Data || Data->LODResources.IsEmpty()) return Json(J);
    const auto& Lod=Data->LODResources[0];
    const auto* DF=Lod.DistanceFieldData;
    auto Distance=MakeShared<FJsonObject>();
    Distance->SetBoolField(TEXT("present"),DF!=nullptr);
    if (DF)
    {
        Distance->SetBoolField(TEXT("valid"),DF->IsValid());
        Distance->SetBoolField(TEXT("asyncBuilding"),DF->bAsyncBuilding);
        Distance->SetNumberField(TEXT("alwaysLoadedBytes"),DF->AlwaysLoadedMip.Num());
        Distance->SetNumberField(TEXT("streamableBytes"),DF->StreamableMips.GetBulkDataSize());
        int64 Bricks=0;
        TArray<TSharedPtr<FJsonValue>> Mips;
        for (const auto& Mip:DF->Mips)
        {
            Bricks+=Mip.NumDistanceFieldBricks;
            auto Row=MakeShared<FJsonObject>();
            Row->SetArrayField(TEXT("indirectionDimensions"),{
                MakeShared<FJsonValueNumber>(Mip.IndirectionDimensions.X),
                MakeShared<FJsonValueNumber>(Mip.IndirectionDimensions.Y),
                MakeShared<FJsonValueNumber>(Mip.IndirectionDimensions.Z)});
            Row->SetNumberField(TEXT("bricks"),Mip.NumDistanceFieldBricks);
            Row->SetNumberField(TEXT("bulkSize"),Mip.BulkSize);
            Mips.Add(MakeShared<FJsonValueObject>(Row));
        }
        Distance->SetNumberField(TEXT("bricks"),Bricks);
        Distance->SetArrayField(TEXT("mips"),Mips);
    }
    J->SetObjectField(TEXT("distanceField"),Distance);
    auto Cards=MakeShared<FJsonObject>();
    const auto* Card=Lod.CardRepresentationData;
    Cards->SetBoolField(TEXT("present"),Card!=nullptr);
    if (Card)
    {
        Cards->SetNumberField(TEXT("count"),Card->MeshCardsBuildData.CardBuildData.Num());
        Cards->SetBoolField(TEXT("finite"),!Card->ContainsNaN());
    }
    J->SetObjectField(TEXT("cards"),Cards);
    auto Ray=MakeShared<FJsonObject>();
#if RHI_RAYTRACING
    // The UObject/render-data lifetime is retained on GT until this queued read completes.
    auto* Geometry=Lod.RayTracingGeometry;
    ENQUEUE_RENDER_COMMAND(WarReadLumenGeometry)([Geometry,Ray](FRHICommandListImmediate&)
    {
        Ray->SetBoolField(TEXT("present"),Geometry!=nullptr);
        if (!Geometry) return;
        Ray->SetBoolField(TEXT("validInitializer"),Geometry->HasValidInitializer());
        Ray->SetBoolField(TEXT("valid"),Geometry->IsValid());
        Ray->SetBoolField(TEXT("rhiPresent"),Geometry->GetRHI()!=nullptr);
        Ray->SetBoolField(TEXT("requiresBuild"),Geometry->GetRequiresBuild());
    });
    FlushRenderingCommands();
#else
    Ray->SetBoolField(TEXT("present"),false);
#endif
    J->SetObjectField(TEXT("rayTracing"),Ray);
    J->SetBoolField(TEXT("available"),true);
    J->SetBoolField(TEXT("runtimeSceneMembershipVerified"),false);
    J->SetBoolField(TEXT("surfaceCacheCoverageVerified"),false);
    return Json(J);
}

FString UWarImportLibrary::DescribeStaticMeshRenderData(UStaticMesh* Mesh)
{
    if (!IsValid(Mesh)) return TEXT("{\"available\":false,\"reason\":\"missingMesh\"}");
    FAssetCompilingManager::Get().FinishAllCompilation();
    const FStaticMeshRenderData* Data = Mesh->GetRenderData();
    auto Report = MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("readOnly"), true);
    Report->SetStringField(TEXT("mesh"), Mesh->GetPathName());
    Report->SetBoolField(TEXT("available"), Data != nullptr);
    if (Data)
    {
        // Reduction LODs often have no source MeshDescription. Their render buffers still carry UVs.
        TMap<FIntVector, TArray<FVector3f>> SourceNormals;
        struct FSourceFace { FVector3f Normals[3]; FVector2f UVs[3]; };
        TMap<FString,TArray<FSourceFace>> SourceFaces;
        const auto PositionKey = [](const FVector3f& P)
        {
            return FIntVector(FMath::RoundToInt(P.X * 10.f), FMath::RoundToInt(P.Y * 10.f), FMath::RoundToInt(P.Z * 10.f));
        };
        const auto FaceKey = [](const FIntVector* P, int32 Material, int32& Rotation)
        {
            FString Best;
            for (int32 Start=0;Start<3;++Start)
            {
                const auto& A=P[Start];const auto& B=P[(Start+1)%3];const auto& C=P[(Start+2)%3];
                const FString Key=FString::Printf(TEXT("%d:%d,%d,%d|%d,%d,%d|%d,%d,%d"),Material,
                    A.X,A.Y,A.Z,B.X,B.Y,B.Z,C.X,C.Y,C.Z);
                if (Best.IsEmpty() || Key<Best) { Best=Key;Rotation=Start; }
            }
            return Best;
        };
        if (const FMeshDescription* Description = Mesh->GetMeshDescription(0))
        {
            const FStaticMeshConstAttributes Attributes(*Description);
            const auto Positions = Attributes.GetVertexPositions();
            const auto Normals = Attributes.GetVertexInstanceNormals();
            const auto UVs=Attributes.GetVertexInstanceUVs();
            const auto SlotNames=Attributes.GetPolygonGroupMaterialSlotNames();
            for (const FVertexInstanceID Instance : Description->VertexInstances().GetElementIDs())
                SourceNormals.FindOrAdd(PositionKey(Positions[Description->GetVertexInstanceVertex(Instance)])).AddUnique(Normals[Instance]);
            for (const FTriangleID Triangle:Description->Triangles().GetElementIDs())
            {
                const auto Corners=Description->GetTriangleVertexInstances(Triangle);
                FIntVector Keys[3];
                for (int32 Corner=0;Corner<3;++Corner) Keys[Corner]=PositionKey(Positions[Description->GetVertexInstanceVertex(Corners[Corner])]);
                const FName Slot=SlotNames[Description->GetTrianglePolygonGroup(Triangle)];
                const int32 Material=Mesh->GetStaticMaterials().IndexOfByPredicate([&](const FStaticMaterial& Entry) { return Entry.MaterialSlotName==Slot; });
                int32 Rotation=0;const FString Key=FaceKey(Keys,Material,Rotation);
                FSourceFace Face;
                for (int32 Corner=0;Corner<3;++Corner)
                {
                    const FVertexInstanceID Instance=Corners[(Corner+Rotation)%3];
                    Face.Normals[Corner]=Normals[Instance];Face.UVs[Corner]=UVs.Get(Instance,0);
                }
                SourceFaces.FindOrAdd(Key).Add(Face);
            }
        }
        TArray<TSharedPtr<FJsonValue>> Rows;
        for (int32 Lod = 0; Lod < Data->LODResources.Num(); ++Lod)
        {
            const FStaticMeshLODResources& Resource = Data->LODResources[Lod];
            const auto& Positions = Resource.VertexBuffers.PositionVertexBuffer;
            const auto& Vertices = Resource.VertexBuffers.StaticMeshVertexBuffer;
            auto Row = MakeShared<FJsonObject>();
            Row->SetNumberField(TEXT("lod"), Lod);
            Row->SetNumberField(TEXT("vertices"), Positions.GetNumVertices());
            Row->SetNumberField(TEXT("uvChannels"), Vertices.GetNumTexCoords());
            Row->SetNumberField(TEXT("indices"), Resource.IndexBuffer.GetNumIndices());
            const bool Readable = Positions.GetVertexData() && Vertices.GetTangentData() && Vertices.GetTexCoordData()
                && Positions.GetNumVertices() == Vertices.GetNumVertices() && Vertices.GetNumTexCoords() > 0;
            Row->SetBoolField(TEXT("cpuReadable"), Readable);
            if (Readable)
            {
                int32 InvalidPositions = 0, InvalidNormals = 0, InvalidUVs = 0, NonUnitNormals = 0;
                int32 SourceMatched = 0, SourceMissing = 0, SourceDifferent = 0;
                constexpr float NearZeroTolerance = .0001f, OrthogonalityTolerance = .02f;
                // Packed X/Z each introduce rounding error; native Y is reconstructed from both.
                const float UnitTolerances[3] = {.02f, .04f, .02f};
                struct FAxisDiagnostic
                {
                    int32 Finite = 0, NonFinite = 0, NearZero = 0, Unit = 0, NonUnit = 0;
                    float MinimumLength = FLT_MAX, MaximumLength = 0;
                } AxisDiagnostics[3];
                struct FPairDiagnostic
                {
                    int32 Evaluated = 0, Skipped = 0, Orthogonal = 0, NonOrthogonal = 0;
                    float MaximumAbsoluteDot = 0;
                } PairDiagnostics[3];
                const int32 PairAxes[3][2] = {{0,1}, {0,2}, {1,2}};
                const TCHAR* AxisNames[3] = {TEXT("x"), TEXT("y"), TEXT("z")};
                const TCHAR* PairNames[3] = {TEXT("xy"), TEXT("xz"), TEXT("yz")};
                constexpr int32 BadVertexSampleLimit = 64;
                TArray<TSharedPtr<FJsonValue>> BadVertexSamples;
                const auto JsonScalar = [](float Value) -> TSharedPtr<FJsonValue>
                {
                    if (FMath::IsFinite(Value)) return MakeShared<FJsonValueNumber>(Value);
                    return MakeShared<FJsonValueNull>();
                };
                const auto JsonVector = [&JsonScalar](const FVector3f& Value)
                { return TArray<TSharedPtr<FJsonValue>>{JsonScalar(Value.X), JsonScalar(Value.Y), JsonScalar(Value.Z)}; };
                int32 InvalidBases = 0, OrthogonalBases = 0;
                FVector2f UVMin(FLT_MAX, FLT_MAX), UVMax(-FLT_MAX, -FLT_MAX);
                for (uint32 Vertex = 0; Vertex < Positions.GetNumVertices(); ++Vertex)
                {
                    const FVector3f P = Positions.VertexPosition(Vertex);
                    const FVector3f N(Vertices.VertexTangentZ(Vertex));
                    const FVector3f Basis[3] = {FVector3f(Vertices.VertexTangentX(Vertex)), Vertices.VertexTangentY(Vertex), N};
                    bool ValidAxes[3], FiniteAxes[3] = {}, NearZeroAxes[3] = {}, UnitAxes[3] = {};
                    bool EvaluatedPairs[3] = {}, NonOrthogonalPairs[3] = {};
                    float PairDots[3] = {};
                    bool ValidBasis = true, OrthogonalBasis = true;
                    for (int32 Axis = 0; Axis < 3; ++Axis)
                    {
                        auto& Diagnostic = AxisDiagnostics[Axis];
                        const auto& Vector = Basis[Axis];
                        const bool Finite = FMath::IsFinite(Vector.X) && FMath::IsFinite(Vector.Y) && FMath::IsFinite(Vector.Z);
                        const bool NearZero = Finite && Vector.IsNearlyZero(NearZeroTolerance);
                        FiniteAxes[Axis] = Finite; NearZeroAxes[Axis] = NearZero;
                        ValidAxes[Axis] = Finite && !NearZero;
                        if (!Finite) { ++Diagnostic.NonFinite; ValidBasis = false; continue; }
                        ++Diagnostic.Finite;
                        if (NearZero) ++Diagnostic.NearZero;
                        const float SquaredLength = Vector.SizeSquared(), Length = FMath::Sqrt(SquaredLength);
                        Diagnostic.MinimumLength = FMath::Min(Diagnostic.MinimumLength, Length);
                        Diagnostic.MaximumLength = FMath::Max(Diagnostic.MaximumLength, Length);
                        UnitAxes[Axis] = FMath::Abs(SquaredLength - 1.f) <= UnitTolerances[Axis];
                        if (UnitAxes[Axis]) ++Diagnostic.Unit;
                        else { ++Diagnostic.NonUnit; ValidBasis = false; }
                    }
                    for (int32 Pair = 0; Pair < 3; ++Pair)
                    {
                        auto& Diagnostic = PairDiagnostics[Pair];
                        const int32 A = PairAxes[Pair][0], B = PairAxes[Pair][1];
                        if (!ValidAxes[A] || !ValidAxes[B]) { ++Diagnostic.Skipped; OrthogonalBasis = false; continue; }
                        const float Dot = FMath::Abs(FVector3f::DotProduct(Basis[A], Basis[B]) / (Basis[A].Size() * Basis[B].Size()));
                        EvaluatedPairs[Pair] = true; PairDots[Pair] = Dot; NonOrthogonalPairs[Pair] = Dot > OrthogonalityTolerance;
                        ++Diagnostic.Evaluated;
                        Diagnostic.MaximumAbsoluteDot = FMath::Max(Diagnostic.MaximumAbsoluteDot, Dot);
                        if (Dot <= OrthogonalityTolerance) ++Diagnostic.Orthogonal;
                        else { ++Diagnostic.NonOrthogonal; ValidBasis = false; OrthogonalBasis = false; }
                    }
                    if (OrthogonalBasis) ++OrthogonalBases;
                    if (!ValidBasis)
                    {
                        ++InvalidBases;
                        if (BadVertexSamples.Num() < BadVertexSampleLimit)
                        {
                            auto Sample = MakeShared<FJsonObject>(), AxisFlags = MakeShared<FJsonObject>(), PairFlags = MakeShared<FJsonObject>();
                            Sample->SetNumberField(TEXT("index"), Vertex); Sample->SetArrayField(TEXT("position"), JsonVector(P));
                            const FVector2f UV0 = Vertices.GetVertexUV(Vertex, 0);
                            Sample->SetArrayField(TEXT("uv0"), {JsonScalar(UV0.X), JsonScalar(UV0.Y)});
                            for (int32 Axis = 0; Axis < 3; ++Axis)
                            {
                                Sample->SetArrayField(AxisNames[Axis], JsonVector(Basis[Axis]));
                                auto Flag = MakeShared<FJsonObject>();
                                Flag->SetBoolField(TEXT("nonFinite"), !FiniteAxes[Axis]); Flag->SetBoolField(TEXT("nearZero"), NearZeroAxes[Axis]);
                                Flag->SetBoolField(TEXT("nonUnit"), FiniteAxes[Axis] && !UnitAxes[Axis]);
                                Flag->SetBoolField(TEXT("failed"), !FiniteAxes[Axis] || !UnitAxes[Axis]); AxisFlags->SetObjectField(AxisNames[Axis], Flag);
                                auto PairFlag = MakeShared<FJsonObject>();
                                PairFlag->SetBoolField(TEXT("skipped"), !EvaluatedPairs[Axis]); PairFlag->SetBoolField(TEXT("nonOrthogonal"), NonOrthogonalPairs[Axis]);
                                PairFlag->SetBoolField(TEXT("failed"), !EvaluatedPairs[Axis] || NonOrthogonalPairs[Axis]);
                                if (EvaluatedPairs[Axis]) PairFlag->SetNumberField(TEXT("absoluteNormalizedDot"), PairDots[Axis]);
                                PairFlags->SetObjectField(PairNames[Axis], PairFlag);
                            }
                            Sample->SetObjectField(TEXT("axisFlags"), AxisFlags); Sample->SetObjectField(TEXT("pairFlags"), PairFlags);
                            BadVertexSamples.Add(MakeShared<FJsonValueObject>(Sample));
                        }
                    }
                    if (P.ContainsNaN()) ++InvalidPositions;
                    if (N.ContainsNaN()) ++InvalidNormals;
                    else if (FMath::Abs(N.SizeSquared() - 1.f) > .02f) ++NonUnitNormals;
                    for (uint32 Channel = 0; Channel < Vertices.GetNumTexCoords(); ++Channel)
                    {
                        const FVector2f UV = Vertices.GetVertexUV(Vertex, Channel);
                        if (!FMath::IsFinite(UV.X) || !FMath::IsFinite(UV.Y)) ++InvalidUVs;
                        else if (Channel == 0)
                        {
                            UVMin.X = FMath::Min(UVMin.X, UV.X); UVMin.Y = FMath::Min(UVMin.Y, UV.Y);
                            UVMax.X = FMath::Max(UVMax.X, UV.X); UVMax.Y = FMath::Max(UVMax.Y, UV.Y);
                        }
                    }
                    if (Lod == 0)
                    {
                        const auto* Expected = SourceNormals.Find(PositionKey(P));
                        if (!Expected) ++SourceMissing;
                        else if (Expected->ContainsByPredicate([&](const FVector3f& Source) { return FVector3f::DotProduct(N, Source) >= .995f; })) ++SourceMatched;
                        else ++SourceDifferent;
                    }
                }
                Row->SetNumberField(TEXT("invalidPositions"), InvalidPositions);
                Row->SetNumberField(TEXT("invalidNormals"), InvalidNormals);
                Row->SetNumberField(TEXT("nonUnitNormals"), NonUnitNormals);
                Row->SetNumberField(TEXT("invalidUVs"), InvalidUVs);
                auto TangentBasis = MakeShared<FJsonObject>(), Axes = MakeShared<FJsonObject>(), Pairs = MakeShared<FJsonObject>();
                TangentBasis->SetNumberField(TEXT("version"), 1);
                TangentBasis->SetBoolField(TEXT("diagnosticOnly"), true);
                TangentBasis->SetBoolField(TEXT("highPrecision"), Vertices.GetUseHighPrecisionTangentBasis());
                TangentBasis->SetStringField(TEXT("basisSource"), TEXT("actual_render_buffer_x_z_and_native_reconstructed_y"));
                TangentBasis->SetNumberField(TEXT("nearZeroComponentTolerance"), NearZeroTolerance);
                TangentBasis->SetNumberField(TEXT("orthogonalityAbsoluteNormalizedDotTolerance"), OrthogonalityTolerance);
                TangentBasis->SetNumberField(TEXT("invalidVertices"), InvalidBases);
                TangentBasis->SetNumberField(TEXT("orthogonalVertices"), OrthogonalBases);
                TangentBasis->SetArrayField(TEXT("badVertexSamples"), BadVertexSamples);
                TangentBasis->SetNumberField(TEXT("badVertexSampleLimit"), BadVertexSampleLimit);
                TangentBasis->SetBoolField(TEXT("badVertexSamplesTruncated"), InvalidBases > BadVertexSamples.Num());
                TangentBasis->SetStringField(TEXT("sampleComponentPolicy"), TEXT("actual_buffer_values_nonfinite_as_null"));
                for (int32 Axis = 0; Axis < 3; ++Axis)
                {
                    const auto& Diagnostic = AxisDiagnostics[Axis]; auto Value = MakeShared<FJsonObject>();
                    Value->SetNumberField(TEXT("finite"), Diagnostic.Finite); Value->SetNumberField(TEXT("nonFinite"), Diagnostic.NonFinite);
                    Value->SetNumberField(TEXT("nearZero"), Diagnostic.NearZero); Value->SetNumberField(TEXT("unit"), Diagnostic.Unit);
                    Value->SetNumberField(TEXT("nonUnit"), Diagnostic.NonUnit); Value->SetNumberField(TEXT("unitSquaredTolerance"), UnitTolerances[Axis]);
                    if (Diagnostic.Finite)
                    { Value->SetNumberField(TEXT("minimumLength"), Diagnostic.MinimumLength); Value->SetNumberField(TEXT("maximumLength"), Diagnostic.MaximumLength); }
                    Axes->SetObjectField(AxisNames[Axis], Value);
                    const auto& PairDiagnostic = PairDiagnostics[Axis]; auto PairValue = MakeShared<FJsonObject>();
                    PairValue->SetNumberField(TEXT("evaluated"), PairDiagnostic.Evaluated); PairValue->SetNumberField(TEXT("skipped"), PairDiagnostic.Skipped);
                    PairValue->SetNumberField(TEXT("orthogonal"), PairDiagnostic.Orthogonal); PairValue->SetNumberField(TEXT("nonOrthogonal"), PairDiagnostic.NonOrthogonal);
                    PairValue->SetNumberField(TEXT("maximumAbsoluteNormalizedDot"), PairDiagnostic.MaximumAbsoluteDot);
                    Pairs->SetObjectField(PairNames[Axis], PairValue);
                }
                TangentBasis->SetObjectField(TEXT("axes"), Axes); TangentBasis->SetObjectField(TEXT("pairs"), Pairs);
                Row->SetObjectField(TEXT("tangentBasis"), TangentBasis);
                if (Positions.GetNumVertices() > 0 && UVMin.X != FLT_MAX)
                {
                    Row->SetArrayField(TEXT("uv0Min"), {MakeShared<FJsonValueNumber>(UVMin.X), MakeShared<FJsonValueNumber>(UVMin.Y)});
                    Row->SetArrayField(TEXT("uv0Max"), {MakeShared<FJsonValueNumber>(UVMax.X), MakeShared<FJsonValueNumber>(UVMax.Y)});
                }
                if (Lod == 0)
                {
                    Row->SetNumberField(TEXT("committedSourceNormalMatches"), SourceMatched);
                    Row->SetNumberField(TEXT("committedSourcePositionMissing"), SourceMissing);
                    Row->SetNumberField(TEXT("committedSourceNormalDifferent"), SourceDifferent);
                    Row->SetNumberField(TEXT("sourcePositionToleranceCm"), .1);
                    Row->SetNumberField(TEXT("sourceNormalDotThreshold"), .995);
                    int32 MatchedFaces=0,MissingFaces=0,DifferentFaces=0;
                    const FIndexArrayView Indices=Resource.IndexBuffer.GetArrayView();
                    for (const FStaticMeshSection& Section:Resource.Sections)
                    {
                        for (uint32 Triangle=0;Triangle<Section.NumTriangles;++Triangle)
                        {
                            const uint32 First=Section.FirstIndex+Triangle*3;
                            FIntVector Keys[3];uint32 Corners[3];
                            bool Valid=First+2<static_cast<uint32>(Indices.Num());
                            for (int32 Corner=0;Corner<3 && Valid;++Corner)
                            {
                                Corners[Corner]=Indices[First+Corner];Valid=Corners[Corner]<Positions.GetNumVertices();
                                if (Valid) Keys[Corner]=PositionKey(Positions.VertexPosition(Corners[Corner]));
                            }
                            if (!Valid) { ++MissingFaces;continue; }
                            int32 Rotation=0;const FString Key=FaceKey(Keys,Section.MaterialIndex,Rotation);
                            const auto* Expected=SourceFaces.Find(Key);
                            if (!Expected) { ++MissingFaces;continue; }
                            const bool Matched=Expected->ContainsByPredicate([&](const FSourceFace& Face)
                            {
                                for (int32 Corner=0;Corner<3;++Corner)
                                {
                                    const uint32 Vertex=Corners[(Corner+Rotation)%3];
                                    const FVector3f N(Vertices.VertexTangentZ(Vertex));
                                    const FVector2f UV=Vertices.GetVertexUV(Vertex,0),SourceUV=Face.UVs[Corner];
                                    if (FVector3f::DotProduct(N,Face.Normals[Corner])<.995f
                                        || FMath::Abs(UV.X-SourceUV.X)>.0005f+.001f*FMath::Abs(SourceUV.X)
                                        || FMath::Abs(UV.Y-SourceUV.Y)>.0005f+.001f*FMath::Abs(SourceUV.Y)) return false;
                                }
                                return true;
                            });
                            if (Matched) ++MatchedFaces;else ++DifferentFaces;
                        }
                    }
                    Row->SetStringField(TEXT("sourceMatchingPolicy"),TEXT("oriented_triangle_corners_material_and_uv0"));
                    Row->SetNumberField(TEXT("committedSourceTriangleMatches"),MatchedFaces);
                    Row->SetNumberField(TEXT("committedSourceTrianglesMissing"),MissingFaces);
                    Row->SetNumberField(TEXT("committedSourceTrianglesDifferent"),DifferentFaces);
                    Row->SetNumberField(TEXT("sourceUvAbsoluteTolerance"),.0005);
                    Row->SetNumberField(TEXT("sourceUvRelativeTolerance"),.001);
                }
            }
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Report->SetArrayField(TEXT("lods"), Rows);
    }
    FString Json;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    return Json;
}

bool UWarImportLibrary::ConfigureCitadelSurfaceLods(UStaticMesh* Mesh)
{
    if (!IsInGameThread() || !IsValid(Mesh)) return false;
    UPackage* Package = Mesh->GetOutermost();
    const FString Prefix = TEXT("/Game/WorldRebuild/");
    const FString PackageName = Package->GetName();
    if (Mesh->GetOuter() != Package || !PackageName.StartsWith(Prefix)) return false;
    const FString Relative = PackageName.Mid(Prefix.Len());
    FString Collection, Asset;
    const FString CitadelPrefix = TEXT("AegisCitadel_");
    if (!Relative.Split(TEXT("/Meshes/"), &Collection, &Asset)
        || Collection.Len() != CitadelPrefix.Len() + 12 || !Collection.StartsWith(CitadelPrefix)
        || !Asset.StartsWith(TEXT("SM_")) || Asset != Mesh->GetName()) return false;
    for (TCHAR Character : Collection.Mid(CitadelPrefix.Len()))
        if (!FChar::IsDigit(Character) && (Character < TEXT('a') || Character > TEXT('f'))) return false;
    if (Package->GetMetaData().GetValue(Mesh, TEXT("WarCapitalTerrain")) != Collection + TEXT(":") + Asset)
        return false;

    FAssetCompilingManager::Get().FinishAllCompilation();
    if (Mesh->GetNumSourceModels() == 0 || !Mesh->GetMeshDescription(0) || Mesh->LODForCollision != 0) return false;

    // Match StaticMeshEditorSubsystem::SetLods inheritance, then apply the signed policy once.
    Mesh->Modify();
    Mesh->SetNumSourceModels(1);
    FMeshBuildSettings Settings = Mesh->GetSourceModel(0).BuildSettings;
    Settings.bRecomputeNormals = false;
    Settings.bRecomputeTangents = true;
    Settings.bUseMikkTSpace = true;
    Settings.bComputeWeightedNormals = false;
    Settings.bGenerateLightmapUVs = true;
    Settings.SrcLightmapIndex = 0;
    Settings.DstLightmapIndex = 1;
    Settings.MinLightmapResolution = 64;
    Settings.bUseFullPrecisionUVs = true;
    Settings.bUseHighPrecisionTangentBasis = true;
    constexpr float PercentTriangles[] = {1.f, .65f, .3f};
    constexpr float ScreenSizes[] = {1.f, .4f, .15f};
    for (int32 Lod = 0; Lod < 3; ++Lod)
    {
        if (Lod > 0)
        {
            FStaticMeshSourceModel& Added = Mesh->AddSourceModel();
            Added.ReductionSettings = Mesh->GetSourceModel(Lod - 1).ReductionSettings;
        }
        FStaticMeshSourceModel& Source = Mesh->GetSourceModel(Lod);
        Source.BuildSettings = Settings;
        Source.ReductionSettings.PercentTriangles = PercentTriangles[Lod];
        Source.ScreenSize = ScreenSizes[Lod];
    }
    Mesh->SetAutoComputeLODScreenSize(true);
    Mesh->SetLightMapCoordinateIndex(1);
    Mesh->SetLightMapResolution(128);
    Mesh->bAllowCPUAccess = true;
    TArray<FText> Errors;
    // OutErrors makes this one build synchronous; no PostEditChange or package save follows it.
    Mesh->Build(true, &Errors);
    for (const FText& Error : Errors) UE_LOG(LogTemp, Warning, TEXT("Citadel surface LOD build: %s"), *Error.ToString());
    FAssetCompilingManager::Get().FinishAllCompilation();
    const FStaticMeshRenderData* RenderData = Mesh->GetRenderData();
    return Errors.IsEmpty() && RenderData && RenderData->LODResources.Num() == 3;
}

bool UWarImportLibrary::MoveCityGameplayToLevel(const TArray<AActor*>& Actors, ULevelStreaming* Destination)
{
    ULevel* Level = Destination ? Destination->GetLoadedLevel() : nullptr;
    if (!Level || !Level->GetOutermost()->GetName().StartsWith(TEXT("/Game/Cities/Shared/"))) return false;
    for (auto* Actor : Actors)
        if (!IsValid(Actor) || Actor->GetWorld() != Level->OwningWorld || Actor->IsPackageExternal()
            || Actor->GetLevel() == Level || (Actor->GetAttachParentActor() && !Actors.Contains(Actor->GetAttachParentActor()))
            || !Actor->Rename(*Actor->GetName(), Level, REN_Test | REN_DontCreateRedirectors)) return false;
    for (auto* Actor : Actors)
    {
        Actor->GetOutermost()->MarkPackageDirty();
        // AActor::Rename unregisters/re-registers components and updates both level actor arrays.
        if (!Actor->Rename(*Actor->GetName(), Level, REN_DontCreateRedirectors)) return false;
    }
    Level->MarkPackageDirty();
    return true;
}

TArray<AActor*> UWarImportLibrary::CopyCampaignActorsToLevel(const TArray<AActor*>& Actors, ULevelStreaming* Destination)
{
    TArray<AActor*> Copies;
    ULevel* Level = Destination ? Destination->GetLoadedLevel() : nullptr;
    UWorld* World = Level ? Level->OwningWorld : nullptr;
    if (!World || !Level->GetOutermost()->GetName().StartsWith(TEXT("/Game/WorldRebuild/Zones_"))) return Copies;
    for (const auto* Actor : Actors)
    {
        if (!IsValid(Actor) || Actor->GetWorld() != World || Actor->GetAttachParentActor()
            || !Actor->GetOutermost()->GetName().StartsWith(TEXT("/Game/WorldRebuild/Zones_"))
            || !Actor->Tags.ContainsByPredicate([](FName Tag) { return Tag.ToString().StartsWith(TEXT("WarZoneObject_")); })) return Copies;
    }
    for (auto* Source : Actors)
    {
        FActorSpawnParameters Parameters;
        Parameters.Template = Source;
        Parameters.OverrideLevel = Level;
        Parameters.Name = Source->GetFName();
        Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        // Template root transforms are already authored in world coordinates; do not multiply them twice.
        auto* Copy = World->SpawnActor<AActor>(Source->GetClass(), FTransform::Identity, Parameters);
        if (!Copy) return Copies;
        Copy->SetActorTransform(Source->GetActorTransform(), false, nullptr, ETeleportType::TeleportPhysics);
        Copy->SetActorLabel(Source->GetActorLabel());
        Copy->SetFolderPath(Source->GetFolderPath());
        Copies.Add(Copy);
    }
    return Copies;
}

UBoxComponent* UWarImportLibrary::SetCapitalBuildingCollision(AActor* Actor, const int32 Index,
    const FVector Center, const FVector HalfSize, const double YawDegrees)
{
    if (!IsValid(Actor) || !Actor->ActorHasTag(TEXT("WarCapitalBuilding")) || !Actor->GetRootComponent()
        || Index < 0 || Index > 255 || Center.ContainsNaN() || Center.GetAbsMax() > 100000000.0
        || HalfSize.ContainsNaN() || HalfSize.GetMin() <= 0 || HalfSize.GetMax() > 10000000.0
        || !FMath::IsFinite(YawDegrees)) return nullptr;
    const FName Name(*FString::Printf(TEXT("AuthoredCollision_%d"), Index));
    UBoxComponent* Box = FindObject<UBoxComponent>(Actor, *Name.ToString());
    if (Box && !Box->ComponentHasTag(TEXT("WarCapitalBuildingCollision"))) return nullptr;
    if (!Box)
    {
        if (FindObject<UObject>(Actor, *Name.ToString())) return nullptr;
        Box = NewObject<UBoxComponent>(Actor, Name, RF_Transactional);
        Box->ComponentTags.Add(TEXT("WarCapitalBuildingCollision"));
        Actor->AddInstanceComponent(Box);
        Box->SetMobility(Actor->GetRootComponent()->Mobility);
        Box->SetupAttachment(Actor->GetRootComponent());
        Box->RegisterComponent();
    }
    Box->SetWorldTransform(FTransform(FRotator(0, YawDegrees, 0), Center, FVector::OneVector));
    Box->SetBoxExtent(HalfSize);
    Box->SetCollisionProfileName(TEXT("BlockAll"));
    Box->SetGenerateOverlapEvents(false);
    Box->SetHiddenInGame(true);
    Box->SetVisibility(false);
    Actor->MarkPackageDirty();
    return Box;
}

UStaticMesh* UWarImportLibrary::CreateCapitalSurface(const FString& ZoneId, const FString& Surface,
    const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
    const TArray<FVector2D>& UVs, UMaterialInterface* Material, const bool bCollision)
{
    if ((ZoneId != TEXT("aegis_capital") && ZoneId != TEXT("crownward") && ZoneId != TEXT("brightfen_approach") && ZoneId != TEXT("sunmeadow_march")) || (Surface != TEXT("ground") && Surface != TEXT("water") && Surface != TEXT("bed") && Surface != TEXT("roads") && Surface != TEXT("mountain"))
        || bCollision != (Surface != TEXT("water"))) return nullptr;
    return BuildSurface(TEXT("/Game/Capitals/") + ZoneId + TEXT("/Terrain_") + Surface, ZoneId + TEXT(":") + Surface,
        Positions, Indices, Normals, UVs, Material, bCollision);
}

UStaticMesh* UWarImportLibrary::CreateWorldSurface(const FString& Collection, const FString& Key,
    const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
    const TArray<FVector2D>& UVs, UMaterialInterface* Material, const bool bCollision)
{
    return CreateColoredWorldSurface(Collection, Key, Positions, Indices, Normals, UVs, {}, Material, bCollision);
}

UStaticMesh* UWarImportLibrary::CreateColoredWorldSurface(const FString& Collection, const FString& Key,
    const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
    const TArray<FVector2D>& UVs, const TArray<FLinearColor>& VertexColors, UMaterialInterface* Material, const bool bCollision)
{
    const auto SafeKey = [](const FString& Value) {
        if (Value.IsEmpty() || Value.Len() > 120) return false;
        for (const TCHAR C : Value) if (!FChar::IsAlnum(C) && C != TEXT('_')) return false;
        return true;
    };
    if (!SafeKey(Collection) || !SafeKey(Key)) return nullptr;
    return BuildSurface(TEXT("/Game/WorldRebuild/") + Collection + TEXT("/Meshes/") + Key, Collection + TEXT(":") + Key,
        Positions, Indices, Normals, UVs, Material, bCollision, VertexColors);
}

UStaticMesh* UWarImportLibrary::CreateCompositeWorldSurface(const FString& Collection, const FString& Key,
    const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
    const TArray<FVector2D>& UVs, const TArray<FLinearColor>& VertexColors,
    const TArray<int32>& TriangleMaterials, const TArray<UMaterialInterface*>& Materials, const bool bCollision)
{
    for (const FString* Value : {&Collection, &Key})
    {
        if (Value->IsEmpty() || Value->Len() > 120) return nullptr;
        for (TCHAR C : *Value) if (!FChar::IsAlnum(C) && C != TEXT('_')) return nullptr;
    }
    if (Materials.IsEmpty()) return nullptr;
    return BuildSurface(TEXT("/Game/WorldRebuild/") + Collection + TEXT("/Meshes/") + Key, Collection + TEXT(":") + Key,
        Positions, Indices, Normals, UVs, Materials[0], bCollision, VertexColors, TriangleMaterials, Materials);
}

UStaticMesh* UWarImportLibrary::BuildSurface(const FString& PackageName, const FString& Owner,
    const TArray<FVector>& Positions, const TArray<int32>& Indices, const TArray<FVector>& Normals,
    const TArray<FVector2D>& UVs, UMaterialInterface* Material, const bool bCollision,
    const TArray<FLinearColor>& VertexColors, const TArray<int32>& TriangleMaterials,
    const TArray<UMaterialInterface*>& Materials)
{
    if (!Material || Positions.IsEmpty() || Positions.Num() > 2000000 || Positions.Num() != Normals.Num()
        || Positions.Num() != UVs.Num() || Indices.IsEmpty() || Indices.Num() % 3 || Indices.Num() > 6000000
        || (!VertexColors.IsEmpty() && VertexColors.Num() != Positions.Num())) return nullptr;
    const TArray<UMaterialInterface*> Slots = Materials.IsEmpty() ? TArray<UMaterialInterface*>{Material} : Materials;
    if (Slots.Num() > 64 || Slots.Contains(nullptr)
        || (!TriangleMaterials.IsEmpty() && TriangleMaterials.Num() != Indices.Num() / 3)
        || (Slots.Num() > 1 && TriangleMaterials.IsEmpty())) return nullptr;
    for (int32 Index : TriangleMaterials) if (!Slots.IsValidIndex(Index)) return nullptr;
    for (const auto& Color : VertexColors)
        for (float Channel : {Color.R, Color.G, Color.B, Color.A})
            if (!FMath::IsFinite(Channel) || Channel < 0.f || Channel > 1.f) return nullptr;
    for (int32 Index = 0; Index < Positions.Num(); ++Index)
    {
        if (Positions[Index].ContainsNaN() || Positions[Index].GetAbsMax() > 100000000.0
            || Normals[Index].ContainsNaN() || !Normals[Index].IsNormalized()
            || !FMath::IsFinite(UVs[Index].X) || !FMath::IsFinite(UVs[Index].Y)) return nullptr;
    }
    for (int32 Index : Indices) if (!Positions.IsValidIndex(Index)) return nullptr;
    for (int32 Index = 0; Index < Indices.Num(); Index += 3)
    {
        if (FVector::CrossProduct(Positions[Indices[Index + 1]] - Positions[Indices[Index]],
            Positions[Indices[Index + 2]] - Positions[Indices[Index]]).IsNearlyZero()) return nullptr;
    }
    const FString Name = FPackageName::GetShortName(PackageName);
    UPackage* Package = CreatePackage(*PackageName);
    UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *(PackageName + TEXT(".") + Name));
    if (Mesh && Package->GetMetaData().GetValue(Mesh, TEXT("WarCapitalTerrain")) != Owner) return nullptr;
    const bool bCreated = !Mesh;
    if (!Mesh) Mesh = NewObject<UStaticMesh>(Package, *Name, RF_Public | RF_Standalone);
    FMeshDescription Description;
    FStaticMeshAttributes Attributes(Description);
    Attributes.Register();
    auto VertexPositions = Attributes.GetVertexPositions();
    auto VertexNormals = Attributes.GetVertexInstanceNormals();
    auto Tangents = Attributes.GetVertexInstanceTangents();
    auto Signs = Attributes.GetVertexInstanceBinormalSigns();
    auto Colors = Attributes.GetVertexInstanceColors();
    auto VertexUVs = Attributes.GetVertexInstanceUVs();
    VertexUVs.SetNumChannels(1);
    TArray<FPolygonGroupID> Groups;
    TArray<FName> SlotNames;
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
    {
        const FName Slot = Slots.Num() == 1 ? FName(TEXT("Surface")) : FName(*FString::Printf(TEXT("Surface_%d"), Index));
        const FPolygonGroupID Group = Description.CreatePolygonGroup();
        Attributes.GetPolygonGroupMaterialSlotNames()[Group] = Slot;
        Groups.Add(Group); SlotNames.Add(Slot);
    }
    TArray<FVertexID> Vertices;
    Vertices.Reserve(Positions.Num());
    for (const auto& Position : Positions)
    {
        const FVertexID Vertex = Description.CreateVertex();
        VertexPositions[Vertex] = FVector3f(Position);
        Vertices.Add(Vertex);
    }
    for (int32 Index = 0; Index < Indices.Num(); Index += 3)
    {
        TArray<FVertexInstanceID> Corners;
        for (int32 Offset = 0; Offset < 3; ++Offset)
        {
            const int32 Source = Indices[Index + Offset];
            const FVertexInstanceID Instance = Description.CreateVertexInstance(Vertices[Source]);
            VertexNormals[Instance] = FVector3f(Normals[Source]);
            FVector Tangent = FVector::VectorPlaneProject(FVector::YAxisVector, Normals[Source]).GetSafeNormal();
            if (Tangent.IsNearlyZero()) Tangent = FVector::VectorPlaneProject(FVector::XAxisVector, Normals[Source]).GetSafeNormal();
            Tangents[Instance] = FVector3f(Tangent);
            Signs[Instance] = 1.f;
            const FLinearColor Color = VertexColors.IsEmpty() ? FLinearColor::White : VertexColors[Source];
            Colors[Instance] = FVector4f(Color.R, Color.G, Color.B, Color.A);
            VertexUVs.Set(Instance, 0, FVector2f(UVs[Source]));
            Corners.Add(Instance);
        }
        Description.CreateTriangle(Groups[TriangleMaterials.IsEmpty() ? 0 : TriangleMaterials[Index / 3]], Corners);
    }
    Mesh->GetStaticMaterials().Reset();
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
        Mesh->GetStaticMaterials().Add(FStaticMaterial(Slots[Index], SlotNames[Index]));
    if (!Mesh->BuildFromMeshDescriptions({ &Description })) return nullptr;
    if (bCollision)
    {
        Mesh->CreateBodySetup();
        Mesh->GetBodySetup()->CollisionTraceFlag = CTF_UseComplexAsSimple;
        Mesh->GetBodySetup()->bDoubleSidedGeometry = true;
        Mesh->GetBodySetup()->InvalidatePhysicsData();
        Mesh->GetBodySetup()->CreatePhysicsMeshes();
    }
    Package->GetMetaData().SetValue(Mesh, TEXT("WarCapitalTerrain"), *Owner);
    if (bCreated) FAssetRegistryModule::AssetCreated(Mesh);
    Mesh->MarkPackageDirty();
    return Mesh;
}

FBox UWarImportLibrary::GetSkinnedBounds(USkeletalMeshComponent* Component)
{
    FBox Bounds(ForceInit);
    if (!Component) return Bounds;
    const FSkeletalMeshRenderData* RenderData = Component->GetSkeletalMeshRenderData();
    const FSkinWeightVertexBuffer* Weights = Component->GetSkinWeightBuffer(0);
    if (!RenderData || RenderData->LODRenderData.IsEmpty() || !Weights) return Bounds;
    TArray<FMatrix44f> Matrices;
    Component->GetCurrentRefToLocalMatrices(Matrices, 0);
    const auto& LOD = RenderData->LODRenderData[0];
    for (uint32 Index = 0; Index < LOD.GetNumVertices(); ++Index)
        Bounds += FVector(USkeletalMeshComponent::GetSkinnedVertexPosition(Component, Index, LOD, *Weights, Matrices));
    return Bounds;
}

bool UWarImportLibrary::FinalizeAnimationSampling(UAnimSequence* Animation)
{
    if (!IsValid(Animation)) return false;
    Animation->WaitOnExistingCompression();
    Animation->GetController().NotifyPopulated();
    return PrepareCompressedAnimation(Animation);
}

bool UWarImportLibrary::PrepareCompressedAnimation(UAnimSequence* Animation)
{
    if (!IsValid(Animation)) return false;
    Animation->WaitOnExistingCompression();
    Animation->CacheDerivedDataForCurrentPlatform();
    Animation->WaitOnExistingCompression();
    return Animation->IsCompressedDataValid() && Animation->IsBoneCompressedDataValid();
}

void UWarImportLibrary::PreparePreviewFrame(USkeletalMeshComponent* Component)
{
    FAssetCompilingManager::Get().FinishAllCompilation();
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    if (Component)
    {
        // Commandlet review loops do not advance the engine frame. Skeletal
        // evaluation caches must see a new frame for each requested pose.
        ++GFrameCounter;
        Component->TickAnimation(0.f, false);
        Component->RefreshBoneTransforms();
        Component->UpdateComponentToWorld();
        Component->MarkRenderTransformDirty();
        if (UWorld* World = Component->GetWorld()) World->SendAllEndOfFrameUpdates();
    }
    FlushRenderingCommands();
}

void UWarImportLibrary::PrepareWorldPreviewFrame(UWorld* World)
{
    // Each commandlet capture must get a fresh frame for sky, shadow and temporal caches.
    if (World) ++GFrameCounter;
    PreparePreviewFrame(nullptr);
    // Commandlets do not tick the editor world between camera captures.
    if (World) World->SendAllEndOfFrameUpdates();
    FlushRenderingCommands();
}

TArray<FString> UWarImportLibrary::GetStreamingLevelPackageNames(UWorld* World)
{
    TArray<FString> Packages;
    if (!IsValid(World))
    {
        UE_LOG(LogTemp, Error, TEXT("Streaming level package inspection requires a valid world."));
        return Packages;
    }
    Packages.Reserve(World->GetStreamingLevels().Num());
    for (const ULevelStreaming* Level : World->GetStreamingLevels())
    {
        if (!IsValid(Level))
        {
            UE_LOG(LogTemp, Error, TEXT("Streaming level package inspection encountered an invalid declaration."));
            return {};
        }
        Packages.Add(Level->GetWorldAssetPackageName());
    }
    Packages.Sort();
    return Packages;
}

FString UWarImportLibrary::GetSourceAnimationName(const UAnimSequence* Animation)
{
    const UFbxAnimSequenceImportData* Data = Animation
        ? Cast<UFbxAnimSequenceImportData>(Animation->AssetImportData) : nullptr;
    return Data ? Data->SourceAnimationName : FString();
}

UStaticMesh* UWarImportLibrary::CreateProofTerrain(UMaterialInterface* Material)
{
    if (!Material) return nullptr;
    const TCHAR* PackageName = TEXT("/Game/MigrationProof/Terrain");
    UPackage* Package = CreatePackage(PackageName);
    UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/MigrationProof/Terrain.Terrain"));
    if (Mesh && Package->GetMetaData().GetValue(Mesh, TEXT("WarMigrationProof")) != FString(TEXT("schema-1"))) return nullptr;
    if (!Mesh) Mesh = NewObject<UStaticMesh>(Package, TEXT("Terrain"), RF_Public | RF_Standalone);
    FMeshDescription Description;
    FStaticMeshAttributes Attributes(Description);
    Attributes.Register();
    auto Positions = Attributes.GetVertexPositions();
    auto Normals = Attributes.GetVertexInstanceNormals();
    auto Tangents = Attributes.GetVertexInstanceTangents();
    auto Signs = Attributes.GetVertexInstanceBinormalSigns();
    auto Colors = Attributes.GetVertexInstanceColors();
    auto UVs = Attributes.GetVertexInstanceUVs();
    UVs.SetNumChannels(1);
    const FPolygonGroupID Group = Description.CreatePolygonGroup();
    Attributes.GetPolygonGroupMaterialSlotNames()[Group] = TEXT("Ground");
    constexpr int32 Cells = 40;
    TArray<FVertexID> Vertices;
    for (int32 Y = 0; Y <= Cells; ++Y)
    {
        for (int32 X = 0; X <= Cells; ++X)
        {
            const FVertexID Vertex = Description.CreateVertex();
            Positions[Vertex] = FVector3f((X - Cells / 2) * 100.f, (Y - Cells / 2) * 100.f, 0.f);
            Vertices.Add(Vertex);
        }
    }
    for (int32 Y = 0; Y < Cells; ++Y)
    {
        for (int32 X = 0; X < Cells; ++X)
        {
            const int32 A = Y * (Cells + 1) + X;
            const int32 Indices[] = { A, A + Cells + 2, A + 1, A, A + Cells + 1, A + Cells + 2 };
            for (int32 Triangle = 0; Triangle < 2; ++Triangle)
            {
                TArray<FVertexInstanceID> Corners;
                for (int32 Corner = 0; Corner < 3; ++Corner)
                {
                    const FVertexID Vertex = Vertices[Indices[Triangle * 3 + Corner]];
                    const FVertexInstanceID Instance = Description.CreateVertexInstance(Vertex);
                    Normals[Instance] = FVector3f(0, 0, 1);
                    Tangents[Instance] = FVector3f(1, 0, 0);
                    Signs[Instance] = 1.f;
                    Colors[Instance] = FVector4f(1, 1, 1, 1);
                    UVs.Set(Instance, 0, FVector2f(Positions[Vertex].X / 400.f, Positions[Vertex].Y / 400.f));
                    Corners.Add(Instance);
                }
                Description.CreateTriangle(Group, Corners);
            }
        }
    }
    Mesh->GetStaticMaterials().Reset();
    Mesh->GetStaticMaterials().Add(FStaticMaterial(Material, TEXT("Ground")));
    if (!Mesh->BuildFromMeshDescriptions({ &Description })) return nullptr;
    Mesh->CreateBodySetup();
    Mesh->GetBodySetup()->CollisionTraceFlag = CTF_UseComplexAsSimple;
    Mesh->GetBodySetup()->bDoubleSidedGeometry = true;
    Mesh->GetBodySetup()->InvalidatePhysicsData();
    Mesh->GetBodySetup()->CreatePhysicsMeshes();
    FAssetRegistryModule::AssetCreated(Mesh);
    Mesh->MarkPackageDirty();
    return Mesh;
}
